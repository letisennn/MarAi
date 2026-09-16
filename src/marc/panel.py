"""Build the observation spine + feature_panel + target_panel.

Weekly observations (Friday close, snapped to the last trading day) for
in-universe names with enough history. Features and targets are computed once per
security from its full daily history and then sampled at the observation dates.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from marc.config import get_logger, targets_config, universe_config
from marc.features import FEATURE_SET_VERSION, compute_feature_frame
from marc.targets.forward_returns import DelistInfo, compute_target_frame

log = get_logger(__name__)

_KIND = {"acquired": "acquisition", "bankrupt": "bankruptcy", "delisted": "delisting"}


def _observation_dates(calendar: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    fridays = pd.date_range(start, end, freq="W-FRI")
    cal = calendar.sort_values()
    idx = cal.searchsorted(fridays, side="right") - 1
    keep = idx >= 0
    snapped = cal[idx[keep].clip(0)]
    within = (fridays[keep] - snapped) <= pd.Timedelta(days=4)
    return sorted(set(snapped[within]))


def _security_frame(con: duckdb.DuckDBPyConnection, sid: int) -> pd.DataFrame:
    df = con.execute(
        """
        SELECT session_date, adj_close_sek, adj_high_sek, adj_low_sek,
               close_local, open_local, volume, turnover_sek, market_cap_sek,
               fx_rate, csf, cdf
        FROM price_clean WHERE security_id = ? ORDER BY session_date
        """,
        [sid],
    ).df()
    if df.empty:
        return df
    df["session_date"] = pd.to_datetime(df["session_date"])
    df = df.set_index("session_date")
    df = df.rename(columns={"adj_close_sek": "adj_close", "adj_high_sek": "adj_high", "adj_low_sek": "adj_low"})
    _attach_attention(con, sid, df)
    _attach_insider_short(con, sid, df)
    return df


def _attach_attention(con: duckdb.DuckDBPyConnection, sid: int, df: pd.DataFrame) -> None:
    """Vecko-attention (search/news/forum) forward-fylld till dagsupplösning, lagd
    en vecka bakåt för att garantera point-in-time (dag t ser veckan före t)."""
    try:
        attn = con.execute(
            "SELECT session_date, channel, value, sentiment FROM attention_daily WHERE security_id = ? "
            "ORDER BY session_date",
            [sid],
        ).df()
    except duckdb.CatalogException:
        return
    if attn.empty:
        return
    attn["session_date"] = pd.to_datetime(attn["session_date"])
    wide = (
        attn.pivot_table(index="session_date", columns="channel", values="value", aggfunc="last")
        .sort_index()
        .shift(1)  # point-in-time: veckan före
        .rename(columns={"search": "attn_search", "news": "attn_news", "forum": "attn_forum"})
    )
    news_sent = (
        attn[attn["channel"] == "news"]
        .drop_duplicates(subset=["session_date"], keep="last")
        .set_index("session_date")["sentiment"]
        .sort_index().shift(1)
        .rename("attn_news_sentiment")
    )
    wide = wide.join(news_sent)
    daily = wide.reindex(wide.index.union(df.index)).sort_index().ffill().reindex(df.index)
    for c in ("attn_search", "attn_news", "attn_forum", "attn_news_sentiment"):
        if c in daily.columns:
            df[c] = daily[c].to_numpy()


def _attach_insider_short(con: duckdb.DuckDBPyConnection, sid: int, df: pd.DataFrame) -> None:
    """Insiderhandel (rullande 90-dagars nettobelopp, kausalt på publiceringsdatum
    — inte transaktionsdatum) + senast kända blankningsnivå (ffill, kausalt).
    Manuellt exporterade FI-register (marc.ingestion.insider_short); tomma
    tabeller ger bara inga kolumner, aldrig ett fel."""
    try:
        ins = con.execute(
            "SELECT coalesce(publication_date, transaction_date) AS d, transaction_type, amount_sek "
            "FROM insider_transaction WHERE security_id = ?",
            [sid],
        ).df()
    except duckdb.CatalogException:
        ins = pd.DataFrame()
    if not ins.empty:
        ins["d"] = pd.to_datetime(ins["d"])
        sign = ins["transaction_type"].map({"buy": 1.0, "sell": -1.0}).fillna(0.0)
        ins["signed"] = sign * pd.to_numeric(ins["amount_sek"], errors="coerce").fillna(0.0)
        daily_net = ins.dropna(subset=["d"]).groupby("d")["signed"].sum().sort_index()
        if not daily_net.empty:
            full = daily_net.reindex(daily_net.index.union(df.index), fill_value=0.0).sort_index()
            roll90 = full.rolling(90, min_periods=1).sum()
            df["insider_net_buy_90d_sek"] = roll90.reindex(df.index).to_numpy()

    try:
        sh = con.execute(
            "SELECT position_date AS d, pct_of_shares FROM short_interest WHERE security_id = ? "
            "ORDER BY position_date",
            [sid],
        ).df()
    except duckdb.CatalogException:
        sh = pd.DataFrame()
    if not sh.empty:
        sh["d"] = pd.to_datetime(sh["d"])
        s = sh.set_index("d")["pct_of_shares"].sort_index()
        daily_s = s.reindex(s.index.union(df.index)).sort_index().ffill().reindex(df.index)
        df["short_interest_pct"] = daily_s.to_numpy()


def _delist_info(sec: pd.Series, frame: pd.DataFrame) -> DelistInfo | None:
    """Acquisition ``status_detail`` is a premium fraction over the last adjusted
    close (the synthetic seed cannot carry real offer prices). A real data source
    would instead supply the actual post-announcement terminal price.
    """
    status = str(sec["status"])
    if status not in _KIND or pd.isna(sec["status_date"]):
        return None
    d = pd.Timestamp(sec["status_date"])
    offer_adj = None
    if status == "acquired" and not frame.empty:
        try:
            premium = float(sec["status_detail"])
        except (TypeError, ValueError):
            premium = 0.25
        prior = frame.loc[frame.index <= d, "adj_close"]
        if len(prior):
            offer_adj = float(prior.iloc[-1]) * (1.0 + premium)
    return DelistInfo(kind=_KIND[status], date=d, offer_adj_sek=offer_adj)


def build_panel(con: duckdb.DuckDBPyConnection) -> dict:
    ucfg = universe_config()
    name = ucfg["universe_name"]
    small_max = float(ucfg["cap_segments"]["small_max_market_cap_sek"])
    min_hist = int(ucfg["min_history_trading_days"])
    start = pd.Timestamp(ucfg["study_start"])
    # study_end tomt/null => kör fram till senaste handelsdag (så panelen alltid är aktuell)
    end = pd.Timestamp(ucfg["study_end"]) if ucfg.get("study_end") else pd.Timestamp.today().normalize()
    tsv = targets_config()["target_set_version"]

    cal = pd.DatetimeIndex(
        pd.to_datetime(
            [r[0] for r in con.execute("SELECT DISTINCT session_date FROM price_clean").fetchall()]
        )
    ).sort_values()
    if len(cal) == 0:
        raise RuntimeError("price_clean empty — run ingestion + cleaning first")
    obs_dates = _observation_dates(cal, start, end)

    iv = con.execute(
        "SELECT security_id, valid_from, valid_to FROM universe_membership WHERE universe_name = ?",
        [name],
    ).df()
    iv["valid_from"] = pd.to_datetime(iv["valid_from"])
    iv["valid_to"] = pd.to_datetime(iv["valid_to"])
    members = {sid: g[["valid_from", "valid_to"]].to_records(index=False) for sid, g in iv.groupby("security_id")}

    secs = con.execute(
        "SELECT security_id, isin, status, CAST(status_date AS DATE) AS status_date, status_detail FROM security"
    ).df()

    con.execute(
        "DELETE FROM feature_panel WHERE obs_id IN (SELECT obs_id FROM observation WHERE universe_name = ?)",
        [name],
    )
    con.execute(
        "DELETE FROM target_panel WHERE obs_id IN (SELECT obs_id FROM observation WHERE universe_name = ?)",
        [name],
    )
    con.execute("DELETE FROM observation WHERE universe_name = ?", [name])

    obs_rows, feat_rows, tgt_rows = [], [], []
    n_sec = 0
    for _, sec in secs.iterrows():
        sid = int(sec["security_id"])
        if sid not in members:
            continue
        frame = _security_frame(con, sid)
        if len(frame) < min_hist:
            continue
        n_sec += 1
        feats = compute_feature_frame(frame)
        tgts = compute_target_frame(frame, cal, _delist_info(sec, frame))

        spans = members[sid]
        hist_dates = frame.index.to_numpy()
        for d in obs_dates:
            if d not in frame.index:
                continue
            in_u = any(
                (s["valid_from"] <= d) and (pd.isna(s["valid_to"]) or d < s["valid_to"]) for s in spans
            )
            if not in_u:
                continue
            n_before = int(np.searchsorted(hist_dates, np.datetime64(d), side="right"))
            if n_before < min_hist:
                continue
            mc = float(frame.at[d, "market_cap_sek"])
            seg = "small" if mc <= small_max else "mid"
            obs_rows.append(
                {"security_id": sid, "obs_date": d.date(), "universe_name": name,
                 "in_universe": True, "has_min_history": True,
                 "cap_segment_at_entry": seg, "market_cap_sek": mc,
                 "feature_set_version": FEATURE_SET_VERSION}
            )
            frow = feats.loc[d]
            for fn, val in frow.items():
                if pd.notna(val):
                    feat_rows.append({"k_sid": sid, "k_date": d.date(), "feature_name": fn, "value": float(val)})
            trow = tgts.loc[d]
            for tn, val in trow.items():
                if pd.notna(val):
                    tgt_rows.append({"k_sid": sid, "k_date": d.date(), "target_set_version": tsv,
                                     "target_name": tn, "value": float(val)})

    if not obs_rows:
        log.warning("panel: no observations produced")
        return {"observations": 0, "securities": n_sec}

    obs_df = pd.DataFrame(obs_rows)
    con.register("obs_df", obs_df)
    con.execute(
        """
        INSERT INTO observation
            (security_id, obs_date, universe_name, in_universe, has_min_history,
             cap_segment_at_entry, market_cap_sek, feature_set_version)
        SELECT security_id, obs_date, universe_name, in_universe, has_min_history,
               cap_segment_at_entry, market_cap_sek, feature_set_version
        FROM obs_df
        """
    )
    con.unregister("obs_df")

    idmap = con.execute(
        "SELECT obs_id, security_id, obs_date FROM observation WHERE universe_name = ?", [name]
    ).df()
    idmap["obs_date"] = pd.to_datetime(idmap["obs_date"]).dt.date
    idmap = idmap.set_index(["security_id", "obs_date"])["obs_id"].to_dict()

    fdf = pd.DataFrame(feat_rows)
    fdf["obs_id"] = [idmap[(s, d)] for s, d in zip(fdf["k_sid"], fdf["k_date"])]
    con.register("fdf", fdf[["obs_id", "feature_name", "value"]])
    con.execute("INSERT INTO feature_panel (obs_id, feature_name, value) SELECT obs_id, feature_name, value FROM fdf")
    con.unregister("fdf")

    tdf = pd.DataFrame(tgt_rows)
    tdf["obs_id"] = [idmap[(s, d)] for s, d in zip(tdf["k_sid"], tdf["k_date"])]
    con.register("tdf", tdf[["obs_id", "target_set_version", "target_name", "value"]])
    con.execute(
        "INSERT INTO target_panel (obs_id, target_set_version, target_name, value) "
        "SELECT obs_id, target_set_version, target_name, value FROM tdf"
    )
    con.unregister("tdf")

    result = {
        "observations": len(obs_df),
        "securities": n_sec,
        "feature_rows": len(fdf),
        "target_rows": len(tdf),
        "obs_date_range": [str(obs_df["obs_date"].min()), str(obs_df["obs_date"].max())],
    }
    log.info("panel: %s", result)
    return result
