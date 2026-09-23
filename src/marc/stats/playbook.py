"""E1e — "playbook": vad olika lägen historiskt har betytt för en köpare.

Svarar på frågan Jonas ställde 2026-09-23: för varje sida/slutsats i appen —
vad ska vi leta efter när vi köper, vilken tidshorisont, hur stort är ett
rimligt mål och hur djupt kan det gå mot en innan det vänder? Allt räknas ur
den faktiska historiken, inga påhittade måltal.

Grupper (small-segmentet, en rad per bolag × vecka):

* ``band``    — Uppbyggnadspoängens band (Market Radar) + "Redan synligt".
* ``mover``   — stora rörelser (Rörelser & utbrott): topp-10 % över fönstret.
* ``verdict`` — appens slutsatskategorier (Bolag i detalj / Dagens upptäckter),
  samma villkor som ``verdict()`` men på just den veckans mätvärden.

Per grupp, period och horisont: andel som slutade på plus (``win_rate``),
median/snitt/25:e percentil av avkastningen, medianen av bästa punkt och
sämsta dipp inom fönstret, andel som nådde +10 %/+25 % någon gång, andel som
dippade -10 % någon gång (≈ andelen som blivit utslagna med 10x hävstång), och
mediantid till toppen. Beskrivande — överlappande fönster gör att träffarna
inte är oberoende, och universumet är survivorship-biased (bara bolag som finns
kvar), så siffrorna är om något OPTIMISTISKA.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from marc.config import get_logger, setup_score_config, targets_config
from marc.discovery.setup import compute_setup_score_panel
from marc.stats._results import write_result

log = get_logger(__name__)

_HOLDOUT_START = pd.Timestamp("2025-01-01")
_HORIZONS = (5, 20, 60)
_MIN_N = 100
_MOVER_WINDOWS = {"1w": "ret_1w", "1m": "ret_1m", "3m": "ret_3m", "12m": "ret_12m"}


def _band_labels(wide: pd.DataFrame) -> pd.Series:
    cfg = setup_score_config()
    score = compute_setup_score_panel(wide)
    gate = cfg["already_visible_gate"]
    visible = ((wide["dist_52w_high"] >= gate["dist_52w_high_min"])
               & (wide["ret_3m"] >= gate["ret_3m_min"])).fillna(False)

    def label(x: float) -> str | None:
        if pd.isna(x):
            return None
        out = cfg["bands"][0][1]
        for lim, name in cfg["bands"]:
            if x >= lim:
                out = name
        return out

    bands = score.map(label)
    return bands.mask(visible, "Redan synligt")


def _verdict_labels(w: pd.DataFrame) -> pd.Series:
    """Samma beslutsträd som ``verdict()`` i app/_data.py, vektoriserat. Regel-
    träffar räknas för just den veckan (appen tittar 8 veckor bakåt)."""
    # lokal import: marc.signals.rules importerar marc.stats._panel, som drar in
    # marc.stats -> playbook — en toppnivåimport här blir en cirkulär import
    # när någon importerar marc.signals först (t.ex. `marc signals`, pipelinen).
    from marc.signals.rules import _rule_masks

    g = w.get
    masks = _rule_masks(w)
    r1m, r3m, r12m = g("ret_1m"), g("ret_3m"), g("ret_12m")
    dist, rvol, vacc = g("dist_52w_high"), g("rvol_5_60"), g("vol_accel")

    vol_rising = ((vacc > 0) | (rvol >= 1.2)).fillna(False)
    exploded = ((rvol >= 2.0) & (r1m >= 0.15)).fillna(False)
    calm = ((r1m >= -0.06) & (r1m <= 0.15)).fillna(False)

    cats = [
        ("Utbrott pågår", (masks["rule1"] | masks["rule2"]).fillna(False) | exploded),
        ("Nära utbrott", ((dist >= -0.06) & (r3m > 0) & vol_rising & (r1m < 0.20)).fillna(False)),
        ("Under uppbyggnad", (vol_rising & calm & (dist >= -0.38) & (dist <= -0.07)).fillna(False)),
        ("Överhettad", ((r3m >= 0.6) & (dist >= -0.04)).fillna(False)),
        ("Utbombad — möjlig vändning", ((r12m <= -0.30) & (r1m > 0.05) & vol_rising).fillna(False)),
        ("Fallande — ingen vändning", ((r3m <= -0.15) & (r1m <= 0) & (dist <= -0.25)).fillna(False)),
    ]
    out = pd.Series("Ingen signal", index=w.index)
    assigned = pd.Series(False, index=w.index)
    for name, mask in cats:
        take = mask & ~assigned
        out[take] = name
        assigned |= take
    return out


def _mover_groups(w: pd.DataFrame) -> dict[str, pd.Series]:
    """Topp-10 % (per vecka) över respektive fönster, plus varianter för 1 mån."""
    groups: dict[str, pd.Series] = {}
    for win, col in _MOVER_WINDOWS.items():
        if col not in w.columns:
            continue
        thr = w.groupby("obs_date")[col].transform(lambda s: s.quantile(0.9))
        top = (w[col] >= thr) & w[col].notna()
        groups[f"Topp 10 % uppgång {win}"] = top
        if win == "1m":
            groups["Topp 10 % uppgång 1m + volym ≥ 2× normalt"] = top & (w["rvol_5_60"] >= 2.0)
            groups["Topp 10 % uppgång 1m, redan vid årshögsta"] = top & (w["dist_52w_high"] >= -0.05)
            groups["Topp 10 % uppgång 1m, fortf. >15 % under årshögsta"] = top & (w["dist_52w_high"] < -0.15)
    return groups


def _entry_metrics_for(df: pd.DataFrame, horizons: tuple[int, ...], gate_abs: float, gate_frac: float) -> pd.DataFrame:
    """Utfall räknat från KÖPKURSEN (stängning dag t) — inte från E1:s P0
    (5-dagarsmedel). P0 är rätt för att testa signaler, men för en köpare som
    köper på stängningen överdriver den vinsten efter en kraftig uppgång
    (medelkursen ligger under stängningskursen) — och det gynnar just
    utbrottsgrupperna. Samma omsättningsgrind som targets på högsta/lägsta."""
    close = df["adj_close"]
    med60 = df["turnover_sek"].rolling(60, min_periods=20).median()
    gpass = df["turnover_sek"] >= np.maximum(gate_abs, gate_frac * med60)
    hi = df["adj_high"].where(gpass)
    lo = df["adj_low"].where(gpass)
    out = {}
    for h in horizons:
        out[f"e_ret_{h}"] = close.shift(-h) / close - 1.0
        out[f"e_maxret_{h}"] = hi.rolling(h, min_periods=1).max().shift(-h) / close - 1.0
        out[f"e_maxdd_{h}"] = lo.rolling(h, min_periods=1).min().shift(-h) / close - 1.0
    return pd.DataFrame(out, index=df.index)


def attach_entry_metrics(con: duckdb.DuckDBPyConnection, wide: pd.DataFrame) -> pd.DataFrame:
    """Lägger e_ret_h / e_maxret_h / e_maxdd_h (från köpkursen) på ``wide``."""
    cfg = targets_config()
    gate = cfg["turnover_gate_sek"]
    px = con.execute(
        "SELECT security_id, session_date, adj_close_sek AS adj_close, adj_high_sek AS adj_high, "
        "adj_low_sek AS adj_low, turnover_sek FROM price_clean ORDER BY security_id, session_date"
    ).df()
    px["session_date"] = pd.to_datetime(px["session_date"])
    frames = []
    for sid, g in px.groupby("security_id"):
        g = g.set_index("session_date")
        em = _entry_metrics_for(g, _HORIZONS, float(gate["absolute_min"]),
                                float(gate["relative_min_fraction_of_median_60d"]))
        em["security_id"] = sid
        frames.append(em.reset_index().rename(columns={"session_date": "obs_date"}))
    em_all = pd.concat(frames, ignore_index=True)
    key = wide[["security_id", "obs_date"]].reset_index()
    merged = key.merge(em_all, on=["security_id", "obs_date"], how="left").set_index(key.columns[0])
    out = wide.copy()
    for c in em_all.columns:
        if c.startswith("e_"):
            out[c] = merged[c].reindex(out.index)
    return out


def _metrics(g: pd.DataFrame, h: int) -> dict | None:
    r = g[f"e_ret_{h}"].dropna()
    if len(r) < _MIN_N:
        return None
    mx = g[f"e_maxret_{h}"].dropna()
    dd = g[f"e_maxdd_{h}"].dropna()
    out = {
        "n": int(len(r)),
        "win_rate": float((r > 0).mean()),
        "median_ret": float(r.median()),
        "mean_ret": float(r.mean()),
        "p25_ret": float(r.quantile(0.25)),
        "med_max_ret": float(mx.median()) if len(mx) else None,
        "med_max_dd": float(dd.median()) if len(dd) else None,
        "p_reach_10": float((mx >= 0.10).mean()) if len(mx) else None,
        "p_reach_25": float((mx >= 0.25).mean()) if len(mx) else None,
        "p_dip_10": float((dd <= -0.10).mean()) if len(dd) else None,
    }
    for col, key in (("days_to_peak_30", "med_days_to_peak_30"), ("days_to_peak_90", "med_days_to_peak_90")):
        if col in g.columns and g[col].notna().any():
            out[key] = float(g[col].median())
    return out


def playbook_rows(wide: pd.DataFrame) -> list[dict]:
    """Alla playbook-rader som platt lista (testbar utan databas). ``wide`` måste ha
    e_ret_h/e_maxret_h/e_maxdd_h — se ``attach_entry_metrics``."""
    w = wide[wide["cap_segment_at_entry"] == "small"].copy()
    w["_period"] = np.where(w["obs_date"] >= _HOLDOUT_START, "holdout", "discovery")

    membership: list[tuple[str, str, pd.Series]] = [("all", "Alla bolag (basnivå)", pd.Series(True, index=w.index))]
    bands = _band_labels(w)
    for b in bands.dropna().unique():
        membership.append(("band", str(b), bands == b))
    verdicts = _verdict_labels(w)
    for v in verdicts.unique():
        membership.append(("verdict", str(v), verdicts == v))
    for name, mask in _mover_groups(w).items():
        membership.append(("mover", name, mask))

    rows: list[dict] = []
    for gtype, group, mask in membership:
        sub = w[mask.fillna(False)]
        for period in ("all", "discovery", "holdout"):
            ps = sub if period == "all" else sub[sub["_period"] == period]
            for h in _HORIZONS:
                m = _metrics(ps, h)
                if m is not None:
                    rows.append({"group_type": gtype, "group": group, "period": period, "horizon": h, **m})
    return rows


def run_playbook(con: duckdb.DuckDBPyConnection, experiment_id: int, wide: pd.DataFrame) -> dict:
    rows = playbook_rows(attach_entry_metrics(con, wide))
    for r in rows:
        params = {k: v for k, v in r.items() if k not in ("group_type", "group", "period", "horizon", "n")}
        write_result(
            con, experiment_id, f"playbook:{r['group_type']}:{r['group']}:{r['period']}:h{r['horizon']}",
            r["win_rate"],
            subset={"group_type": r["group_type"], "group": r["group"], "period": r["period"],
                    "horizon": r["horizon"]},
            n_obs=r["n"], is_out_of_sample=(r["period"] == "holdout"), params=params,
        )
    log.info("E1e playbook: %d rader", len(rows))
    return {"playbook_rows": len(rows)}
