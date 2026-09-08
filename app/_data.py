"""Read-only dataåtkomst för Streamlit-appen.

Appen skriver ALDRIG. All research-logik ligger i paketet ``marc``; den här
modulen kör bara SQL mot ``data/marc.duckdb``, cachar resultaten och översätter
kolumnnamn / mått till klarspråk för gränssnittet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from marc.config import get_settings, universe_config  # noqa: E402
from marc.score import assess as _assess  # noqa: E402

# --------------------------------------------------------------------------- #
# klarspråk
# --------------------------------------------------------------------------- #

COUNTRY_SV = {"SE": "Sverige", "NO": "Norge", "DK": "Danmark", "FI": "Finland"}

# horisont -> vilket "stor uppgång"-event E1d-reglerna utvärderar
HORIZON_EVENT = {
    "5d": "up_10_5d",
    "20d": "up_25_20d",
    "30d": "up_50_30d",
    "60d": "up_50_60d",
    "90d": "up_50_90d",
    "180d": "up_100_180d",
}

# klarspråk per event-kod (som de lagras i experiment_result)
EVENT_CODE_SV = {
    "up_10_5d": "minst +10 % inom en vecka",
    "up_25_20d": "minst +25 % inom en månad",
    "up_50_30d": "minst +50 % inom sex veckor",
    "up_50_60d": "minst +50 % inom tre månader",
    "up_50_90d": "minst +50 % inom ~fyra månader",
    "up_100_180d": "minst +100 % inom ~nio månader",
}

# klarspråk för varje horisont
EVENT_SV = {
    "5d": "minst +10 % inom en vecka",
    "20d": "minst +25 % inom en månad",
    "30d": "minst +50 % inom sex veckor",
    "60d": "minst +50 % inom tre månader",
    "90d": "minst +50 % inom ~fyra månader",
    "180d": "minst +100 % inom ~nio månader",
}

# kort etikett för diagramaxlar
EVENT_SHORT = {
    "5d": "+10 %<br>1 vecka",
    "20d": "+25 %<br>1 månad",
    "30d": "+50 %<br>6 veckor",
    "60d": "+50 %<br>3 mån",
    "90d": "+50 %<br>~4 mån",
    "180d": "+100 %<br>~9 mån",
}

_HZ_ORDER = {"5d": 0, "20d": 1, "30d": 2, "60d": 3, "90d": 4, "180d": 5}

STATUS_SV = {
    "listed": "Aktiv",
    "acquired": "Uppköpt",
    "bankrupt": "Konkurs",
    "delisted": "Avnoterad",
    "suspended": "Handelsstopp",
}

# feature_name -> (svensk etikett, formattyp)
FEATURE_SV: dict[str, tuple[str, str]] = {
    "ret_1w": ("Avkastning 1 vecka", "pct"),
    "ret_1m": ("Avkastning 1 månad", "pct"),
    "ret_3m": ("Avkastning 3 månader", "pct"),
    "ret_6m": ("Avkastning 6 månader", "pct"),
    "ret_12m": ("Avkastning 12 månader", "pct"),
    "dist_52w_high": ("Avstånd till 52-veckors högsta", "pct"),
    "breakout_20d": ("Ny 20-dagarshögsta", "bool"),
    "gap_freq_20d": ("Andel dagar med kursgap (20d)", "pct"),
    "rvol_5_60": ("Relativ volym (5d mot 60d)", "x"),
    "rvol_20_200": ("Relativ volym (20d mot 200d)", "x"),
    "vol_trend_60d": ("Volymtrend 60 dagar", "num"),
    "vol_accel": ("Volymacceleration", "num"),
    "rv_20d": ("Rörlighet 20 dagar (årlig volatilitet)", "pct"),
    "rv_60d": ("Rörlighet 60 dagar (årlig volatilitet)", "pct"),
    "vol_expansion": ("Volatilitetsexpansion (20d/60d)", "x"),
    "amihud_20d": ("Amihud-illikviditet (20d)", "num"),
    "log_mktcap": ("Börsvärde (log)", "num"),
    "log_price_local": ("Kurs (log, lokal)", "num"),
}

# regelnyckel -> klarspråk. Villkoren är förregistrerade i docs/experiments/E1.md §E1d.
RULE_SV: dict[str, dict[str, str]] = {
    "rule1": {
        "titel": "Kraftig volymökning med stark månad och tilltagande rörlighet",
        "villkor": "Relativ volym (5d/60d) ≥ 3×  ·  1-månadersavkastning > +20 %  ·  volatilitetsexpansion ≥ 1,5×",
    },
    "rule2": {
        "titel": "Utbrott till ny 20-dagarshögsta på hög volym",
        "villkor": "Ny 20-dagarshögsta  ·  relativ volym (20d/200d) ≥ 2×",
    },
    "rule3": {
        "titel": "Nära 52-veckors högsta med positiv trend och stigande volym",
        "villkor": "Inom 5 % från 52-veckors högsta  ·  3-månadersavkastning > 0  ·  positiv volymacceleration",
    },
}


def feature_label(name: str) -> str:
    return FEATURE_SV.get(name, (name, "num"))[0]


def pct_vs_normal(ratio: float | None) -> str:
    """En kvot där 1,0 = normalt -> klarspråk i procent."""
    if ratio is None or (isinstance(ratio, float) and pd.isna(ratio)):
        return "–"
    d = ratio - 1.0
    if abs(d) < 0.10:
        return "på normal nivå"
    return f"{abs(d) * 100:.0f} % {'högre' if d > 0 else 'lägre'} än normalt"


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value))


def fmt_feature(name: str, value) -> str:
    """Formatera ett råvärde till en läsbar sträng."""
    if _is_missing(value):
        return "—"
    kind = FEATURE_SV.get(name, (name, "num"))[1]
    if kind == "pct":
        return f"{value * 100:+.1f} %"
    if kind == "x":
        return f"{value:.2f}×"
    if kind == "bool":
        return "Ja" if value >= 0.5 else "Nej"
    return f"{value:.3f}"


def interpret_feature(name: str, value) -> str:
    """En kort mening i klartext om vad värdet betyder. Inga framåtblickande påståenden."""
    if _is_missing(value):
        return ""
    if name.startswith("ret_"):
        if value > 0.001:
            return "kursen är upp under perioden"
        if value < -0.001:
            return "kursen är ned under perioden"
        return "kursen är i stort sett oförändrad"
    if name == "dist_52w_high":
        if value >= -0.05:
            return "handlas mycket nära årshögsta"
        if value >= -0.15:
            return "handlas nära årshögsta"
        if value >= -0.30:
            return "en bit under årshögsta"
        return "långt under årshögsta"
    if name in ("rvol_5_60", "rvol_20_200"):
        if value >= 3:
            return "kraftigt förhöjd handel"
        if value >= 1.5:
            return "förhöjd handel"
        if value >= 0.7:
            return "handel på normal nivå"
        return "låg handel"
    if name in ("rv_20d", "rv_60d"):
        if value >= 0.6:
            return "mycket rörlig kurs"
        if value >= 0.35:
            return "rörlig kurs"
        return "lugn kurs"
    if name == "vol_expansion":
        if value >= 1.5:
            return "rörligheten ökar"
        if value <= 0.8:
            return "rörligheten minskar"
        return "oförändrad rörlighet"
    if name == "breakout_20d":
        return "ny 20-dagarshögsta noterad" if value >= 0.5 else "ingen ny 20-dagarshögsta"
    if name in ("vol_accel", "vol_trend_60d"):
        if value > 0:
            return "stigande handel"
        if value < 0:
            return "fallande handel"
        return "oförändrad handel"
    if name == "gap_freq_20d":
        return "hoppig kurs" if value >= 0.25 else "få kursgap"
    return ""


# --------------------------------------------------------------------------- #
# anslutning + primitiver
# --------------------------------------------------------------------------- #


def db_path() -> Path:
    return get_settings().abs_db_path


def db_exists() -> bool:
    return db_path().exists()


@st.cache_resource
def get_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path()), read_only=True)


@st.cache_data(ttl=60)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    return get_con().execute(sql, list(params)).df()


@st.cache_data(ttl=60)
def scalar(sql: str, params: tuple = ()):
    row = get_con().execute(sql, list(params)).fetchone()
    return None if row is None else row[0]


@st.cache_data(ttl=60)
def universe_name() -> str:
    try:
        return universe_config()["universe_name"]
    except Exception:  # noqa: BLE001
        return "nordic_smallcap_v1"


@st.cache_data(ttl=60)
def data_source() -> str | None:
    return scalar("SELECT source FROM ingestion_run ORDER BY run_id DESC LIMIT 1")


def is_synthetic() -> bool:
    return data_source() == "synthetic"


@st.cache_data(ttl=60)
def latest_obs_date():
    return scalar("SELECT max(obs_date) FROM observation")


@st.cache_data(ttl=60)
def last_signal_date():
    return scalar("SELECT max(as_of_date) FROM signal_log")


@st.cache_data(ttl=60)
def kpis() -> dict:
    return {
        "n_securities": scalar("SELECT count(*) FROM security"),
        "n_dead": scalar("SELECT count(*) FROM security WHERE status <> 'listed'"),
        "n_in_universe_now": scalar(
            "SELECT count(DISTINCT security_id) FROM observation "
            "WHERE obs_date = (SELECT max(obs_date) FROM observation)"
        ),
        "n_obs": scalar("SELECT count(*) FROM observation"),
        "obs_lo": scalar("SELECT min(obs_date) FROM observation"),
        "obs_hi": scalar("SELECT max(obs_date) FROM observation"),
        "last_signal": last_signal_date(),
        "source": data_source(),
    }


@st.cache_data(ttl=60)
def pipeline_status() -> pd.DataFrame:
    tables = {
        "security": "Bolag",
        "price_daily": "Prisrader (dag)",
        "corporate_action": "Bolagshändelser",
        "universe_membership": "Universum-intervall",
        "observation": "Observationer",
        "feature_panel": "Mätvärden",
        "target_panel": "Utfall (framåt)",
        "experiment_result": "Forskningsresultat",
        "signal_log": "Signaler",
        "signal_outcome": "Signalutfall",
    }
    con = get_con()
    rows = []
    for t, label in tables.items():
        try:
            n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        except Exception:  # noqa: BLE001
            n = None
        rows.append({"Tabell": label, "Rader": n})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# bolagslista / screener
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=60)
def screener(weeks: int = 8) -> pd.DataFrame:
    """En rad per bolag: senaste mätvärden + hur många regler som lyst de senaste ``weeks`` veckorna."""
    sql = """
    WITH hi AS (SELECT max(obs_date) AS d FROM observation),
    recent AS (
        SELECT DISTINCT obs_date FROM observation ORDER BY obs_date DESC LIMIT ?
    ),
    last_obs AS (
        SELECT security_id, max(obs_date) AS obs_date FROM observation GROUP BY 1
    ),
    obs_row AS (
        SELECT o.security_id, o.obs_id, o.obs_date, o.market_cap_sek, o.cap_segment_at_entry
        FROM observation o
        JOIN last_obs l ON l.security_id = o.security_id AND l.obs_date = o.obs_date
    ),
    feat AS (
        SELECT obs_id,
            max(value) FILTER (WHERE feature_name = 'ret_1m')        AS ret_1m,
            max(value) FILTER (WHERE feature_name = 'ret_3m')        AS ret_3m,
            max(value) FILTER (WHERE feature_name = 'ret_12m')       AS ret_12m,
            max(value) FILTER (WHERE feature_name = 'dist_52w_high') AS dist_52w_high,
            max(value) FILTER (WHERE feature_name = 'rvol_5_60')     AS rvol_5_60,
            max(value) FILTER (WHERE feature_name = 'rv_20d')        AS rv_20d
        FROM feature_panel
        WHERE obs_id IN (SELECT obs_id FROM obs_row)
        GROUP BY obs_id
    ),
    sig AS (
        SELECT sl.security_id,
               count(DISTINCT split_part(sl.rule_version, ':', -1)) AS n_rules,
               max(sl.as_of_date) AS last_signal
        FROM signal_log sl
        WHERE sl.as_of_date >= (SELECT min(obs_date) FROM recent)
        GROUP BY 1
    )
    SELECT s.security_id, s.name, s.country, s.sector, s.status,
           orw.obs_date                                       AS obs_date,
           orw.market_cap_sek                                 AS market_cap_sek,
           orw.cap_segment_at_entry                           AS segment,
           coalesce(orw.obs_date = (SELECT d FROM hi), FALSE) AS in_universe_now,
           f.ret_1m, f.ret_3m, f.ret_12m, f.dist_52w_high, f.rvol_5_60, f.rv_20d,
           coalesce(sig.n_rules, 0)                           AS n_rules,
           sig.last_signal                                    AS last_signal
    FROM security s
    LEFT JOIN obs_row orw ON orw.security_id = s.security_id
    LEFT JOIN feat f      ON f.obs_id = orw.obs_id
    LEFT JOIN sig         ON sig.security_id = s.security_id
    ORDER BY coalesce(sig.n_rules, 0) DESC, orw.market_cap_sek DESC NULLS LAST, s.name
    """
    df = q(sql, (weeks,))
    df["status_sv"] = df["status"].map(STATUS_SV).fillna(df["status"])
    return df


# --------------------------------------------------------------------------- #
# ett bolag
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=60)
def security_list() -> pd.DataFrame:
    return q(
        "SELECT security_id, name, country, sector, status, status_date "
        "FROM security ORDER BY name"
    )


@st.cache_data(ttl=60)
def security_overview(sid: int) -> dict:
    base = q(
        """
        SELECT security_id, name, country, sector, industry, currency,
               base_listing_mic AS mic, status, status_date, status_detail,
               first_listed_date
        FROM security WHERE security_id = ?
        """,
        (sid,),
    )
    if base.empty:
        return {}
    row = base.iloc[0].to_dict()
    last = q(
        """
        SELECT session_date, close_local, adj_close_sek, market_cap_sek, turnover_sek
        FROM price_clean WHERE security_id = ? ORDER BY session_date DESC LIMIT 1
        """,
        (sid,),
    )
    if not last.empty:
        row.update(last.iloc[0].to_dict())
    o = q(
        "SELECT min(obs_date) lo, max(obs_date) hi, count(*) n "
        "FROM observation WHERE security_id = ?",
        (sid,),
    )
    row["obs_lo"] = o.iloc[0]["lo"]
    row["obs_hi"] = o.iloc[0]["hi"]
    row["n_obs"] = int(o.iloc[0]["n"])
    row["status_sv"] = STATUS_SV.get(row["status"], row["status"])
    return row


@st.cache_data(ttl=60)
def security_prices(sid: int) -> pd.DataFrame:
    df = q(
        """
        SELECT session_date, close_local, adj_close_sek, volume, turnover_sek, market_cap_sek
        FROM price_clean WHERE security_id = ? ORDER BY session_date
        """,
        (sid,),
    )
    if not df.empty:
        df["session_date"] = pd.to_datetime(df["session_date"])
    return df


@st.cache_data(ttl=60)
def security_features_latest(sid: int) -> tuple[object, dict]:
    o = q(
        "SELECT obs_id, obs_date FROM observation WHERE security_id = ? "
        "ORDER BY obs_date DESC LIMIT 1",
        (sid,),
    )
    if o.empty:
        return None, {}
    obs_id = int(o.iloc[0]["obs_id"])
    f = q("SELECT feature_name, value FROM feature_panel WHERE obs_id = ?", (obs_id,))
    return o.iloc[0]["obs_date"], dict(zip(f["feature_name"], f["value"], strict=False))


@st.cache_data(ttl=60)
def security_feature_history(sid: int) -> pd.DataFrame:
    obs = q(
        "SELECT obs_id, obs_date, cap_segment_at_entry, market_cap_sek "
        "FROM observation WHERE security_id = ? ORDER BY obs_date",
        (sid,),
    )
    if obs.empty:
        return pd.DataFrame()
    f = q(
        "SELECT obs_id, feature_name, value FROM feature_panel "
        "WHERE obs_id IN (SELECT obs_id FROM observation WHERE security_id = ?)",
        (sid,),
    )
    t = q(
        "SELECT obs_id, target_name, value FROM target_panel "
        "WHERE obs_id IN (SELECT obs_id FROM observation WHERE security_id = ?)",
        (sid,),
    )
    fw = f.pivot(index="obs_id", columns="feature_name", values="value") if not f.empty else pd.DataFrame()
    tw = t.pivot(index="obs_id", columns="target_name", values="value") if not t.empty else pd.DataFrame()
    wide = obs.set_index("obs_id").join(fw).join(tw)
    wide["obs_date"] = pd.to_datetime(wide["obs_date"])
    return wide.reset_index(drop=True)


@st.cache_data(ttl=60)
def security_signal_history(sid: int) -> pd.DataFrame:
    return q(
        """
        SELECT sl.signal_id, sl.as_of_date,
               split_part(sl.rule_version, ':', -1) AS rule,
               sl.feature_snapshot,
               so20.realized_return AS ret_20d,
               so90.realized_return AS ret_90d,
               so90.realized_event  AS event_90d
        FROM signal_log sl
        LEFT JOIN signal_outcome so20 ON so20.signal_id = sl.signal_id AND so20.horizon = '20d'
        LEFT JOIN signal_outcome so90 ON so90.signal_id = sl.signal_id AND so90.horizon = '90d'
        WHERE sl.security_id = ?
        ORDER BY sl.as_of_date DESC
        """,
        (sid,),
    )


@st.cache_data(ttl=60)
def has_attention() -> bool:
    try:
        return bool(scalar("SELECT count(*) FROM attention_daily") or 0)
    except Exception:  # noqa: BLE001
        return False


@st.cache_data(ttl=60)
def security_attention(sid: int) -> pd.DataFrame:
    """Vecko-serie per kanal (search 0–100, news/forum antal/vecka) för ett bolag."""
    df = q(
        "SELECT session_date, channel, value FROM attention_daily "
        "WHERE security_id = ? ORDER BY session_date",
        (sid,),
    )
    if df.empty:
        return df
    df["session_date"] = pd.to_datetime(df["session_date"])
    wide = df.pivot_table(index="session_date", columns="channel", values="value", aggfunc="last")
    return wide.rename(
        columns={"search": "Sökintresse", "news": "Nyhetsrubriker/vecka", "forum": "Foruminlägg/vecka"}
    ).reset_index()


@st.cache_data(ttl=60)
def security_corporate_actions(sid: int) -> pd.DataFrame:
    return q(
        "SELECT action_type, ex_date, ratio, cash_amount, currency, source "
        "FROM corporate_action WHERE security_id = ? ORDER BY ex_date",
        (sid,),
    )


@st.cache_data(ttl=60)
def security_listing_history(sid: int) -> pd.DataFrame:
    return q(
        "SELECT status, market_segment, valid_from, valid_to, reason "
        "FROM listing_status_history WHERE security_id = ? ORDER BY valid_from",
        (sid,),
    )


# --------------------------------------------------------------------------- #
# signaler
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=60)
def active_signals(weeks: int = 8) -> pd.DataFrame:
    return q(
        """
        WITH recent AS (
            SELECT DISTINCT obs_date FROM observation ORDER BY obs_date DESC LIMIT ?
        )
        SELECT s.name, s.country, s.sector, s.security_id,
               sl.as_of_date,
               split_part(sl.rule_version, ':', -1) AS rule,
               sl.feature_snapshot
        FROM signal_log sl
        JOIN security s USING (security_id)
        WHERE sl.as_of_date >= (SELECT min(obs_date) FROM recent)
        ORDER BY sl.as_of_date DESC, s.name
        """,
        (weeks,),
    )


@st.cache_data(ttl=60)
def recent_signal_log(limit: int = 100) -> pd.DataFrame:
    return q(
        """
        SELECT s.name, sl.as_of_date, sl.security_id,
               split_part(sl.rule_version, ':', -1) AS rule,
               sl.feature_snapshot
        FROM signal_log sl JOIN security s USING (security_id)
        ORDER BY sl.as_of_date DESC, s.name
        LIMIT ?
        """,
        (limit,),
    )


@st.cache_data(ttl=60)
def signal_outcomes() -> pd.DataFrame:
    return q(
        """
        SELECT split_part(sl.rule_version, ':', -1) AS rule,
               so.horizon,
               count(*)                          AS n,
               round(avg(so.realized_return), 4) AS avg_fwd_ret,
               round(avg(CASE WHEN so.realized_event THEN 1.0 ELSE 0.0 END), 4) AS hit_rate
        FROM signal_outcome so JOIN signal_log sl USING (signal_id)
        GROUP BY 1, 2 ORDER BY 1, 2
        """
    )


@st.cache_data(ttl=60)
def fwd90_box() -> pd.DataFrame:
    return q(
        """
        SELECT 'signal (' || split_part(sl.rule_version, ':', -1) || ')' AS grp,
               so.realized_return AS r
        FROM signal_outcome so JOIN signal_log sl USING (signal_id)
        WHERE so.horizon = '90d' AND so.realized_return IS NOT NULL
        UNION ALL
        SELECT 'alla observationer' AS grp, value AS r
        FROM target_panel WHERE target_name = 'fwd_ret_90' AND value IS NOT NULL
        """
    )


# --------------------------------------------------------------------------- #
# forskning (E1)
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=60)
def base_rates() -> pd.DataFrame:
    return q(
        """
        SELECT json_extract_string(subset, '$.event')   AS event,
               json_extract_string(subset, '$.segment') AS segment,
               round(value, 4)   AS rate,
               round(ci_low, 4)  AS ci_low,
               round(ci_high, 4) AS ci_high,
               n_obs, n_events
        FROM experiment_result
        WHERE metric_name LIKE 'base_rate:%'
          AND json_extract_string(subset, '$.slice') = 'pooled'
        ORDER BY event, segment
        """
    )


@st.cache_data(ttl=60)
def base_rate_map() -> dict:
    """{horisont: basnivå} för small-segmentet — hur ofta uppgången sker normalt."""
    br = base_rates()
    small = br[br["segment"] == "small"]
    ev2rate = dict(zip(small["event"], small["rate"], strict=False))
    return {hz: ev2rate.get(ev) for hz, ev in HORIZON_EVENT.items()}


@st.cache_data(ttl=60)
def rule_outcome_stats() -> pd.DataFrame:
    """Per regel × horisont: hur ofta en stor uppgång följde historiskt, och hur
    stora rörelserna blev — jämfört med basnivån. Beskrivande historik, ingen prognos.
    """
    df = q(
        """
        SELECT split_part(sl.rule_version, ':', -1) AS rule,
               so.horizon                           AS horizon,
               count(*)                             AS n,
               avg(CASE WHEN so.realized_event THEN 1.0 ELSE 0.0 END) AS hit_rate,
               median(so.realized_max_return)       AS med_max_ret,
               median(so.realized_max_dd)           AS med_max_dd,
               median(so.realized_return)           AS med_ret
        FROM signal_outcome so JOIN signal_log sl USING (signal_id)
        GROUP BY 1, 2
        """
    )
    if df.empty:
        return df
    brm = base_rate_map()
    df["base_rate"] = df["horizon"].map(brm)
    df["lift"] = df["hit_rate"] / df["base_rate"]
    df["ord"] = df["horizon"].map(_HZ_ORDER)
    return df.sort_values(["rule", "ord"]).reset_index(drop=True)


@st.cache_data(ttl=60)
def panel_forward_ranges() -> dict:
    """Panelbrett historiskt spann (small): median max-uppgång / max-nedgång / avkastning inom ~4 mån."""
    df = q(
        """
        WITH t AS (
            SELECT o.obs_id,
                max(CASE WHEN tp.target_name='fwd_max_ret_90' THEN tp.value END) AS mret,
                max(CASE WHEN tp.target_name='fwd_max_dd_90'  THEN tp.value END) AS mdd,
                max(CASE WHEN tp.target_name='fwd_ret_90'     THEN tp.value END) AS ret
            FROM observation o JOIN target_panel tp USING (obs_id)
            WHERE o.cap_segment_at_entry = 'small'
            GROUP BY 1
        )
        SELECT median(mret) AS med_max_ret, median(mdd) AS med_max_dd,
               median(ret) AS med_ret, quantile_cont(mret, 0.75) AS p75_max_ret
        FROM t
        """
    )
    return {} if df.empty else df.iloc[0].to_dict()


@st.cache_data(ttl=60)
def peer_features_latest() -> pd.DataFrame:
    """Wide-ram: en rad per bolag som har en observation senaste veckan, kolumn per mått."""
    long = q(
        """
        SELECT o.security_id, fp.feature_name, fp.value
        FROM observation o JOIN feature_panel fp USING (obs_id)
        WHERE o.obs_date = (SELECT max(obs_date) FROM observation)
        """
    )
    if long.empty:
        return pd.DataFrame()
    return long.pivot(index="security_id", columns="feature_name", values="value")


@st.cache_data(ttl=60)
def _rules_by_security(weeks: int = 8) -> dict:
    df = q(
        """
        WITH recent AS (SELECT DISTINCT obs_date FROM observation ORDER BY obs_date DESC LIMIT ?)
        SELECT security_id, count(DISTINCT split_part(rule_version, ':', -1)) AS n
        FROM signal_log
        WHERE as_of_date >= (SELECT min(obs_date) FROM recent)
        GROUP BY 1
        """,
        (weeks,),
    )
    return dict(zip(df["security_id"], df["n"], strict=False))


@st.cache_data(ttl=60)
def all_scores(weeks: int = 8) -> pd.DataFrame:
    """Preliminär composite-score för varje bolag med mätvärden senaste veckan."""
    peers = peer_features_latest()
    if peers.empty:
        return pd.DataFrame(columns=["security_id", "score", "band"])
    rmap = _rules_by_security(weeks)
    rows = []
    for sid, frow in peers.iterrows():
        b = _assess(frow.to_dict(), peers, int(rmap.get(sid, 0)))
        rows.append({"security_id": int(sid), "score": b.total, "band": b.band})
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def stock_assessment(sid: int, weeks: int = 8) -> dict:
    """Full bedömning för ett bolag: composite-score + uppdelning + historiskt rörelsespann."""
    obs_date, feats = security_features_latest(sid)
    peers = peer_features_latest()
    rmap = _rules_by_security(weeks)
    n_rules = int(rmap.get(sid, 0))
    out: dict = {"obs_date": obs_date, "has_feats": bool(feats)}
    if not feats or peers.empty:
        return out

    b = _assess(feats, peers, n_rules)
    out["score"] = b.total
    out["band"] = b.band
    out["score_version"] = b.score_version
    out["components"] = [
        {"key": c.key, "label": c.label, "score": c.score, "weight": c.weight, "detail": c.detail}
        for c in b.components
    ]

    # historiskt rörelsespann inom ~4 mån för "bolag i det här läget"
    hist = security_signal_history(sid)
    stats = rule_outcome_stats()
    basis = "generellt för ett litet bolag (median i panelen)"
    up = dn = None
    if n_rules > 0 and not hist.empty and not stats.empty and obs_date is not None:
        rd = q("SELECT DISTINCT obs_date FROM observation ORDER BY obs_date DESC LIMIT ?", (weeks,))
        cutoff = pd.to_datetime(rd["obs_date"]).min() if not rd.empty else pd.Timestamp.min
        fired = hist.assign(_d=pd.to_datetime(hist["as_of_date"]))
        fired = fired[fired["_d"] >= cutoff].sort_values("_d")
        if not fired.empty:
            rk = fired.iloc[-1]["rule"]
            rs = stats[(stats["rule"] == rk) & (stats["horizon"] == "90d")]
            if not rs.empty and int(rs["n"].iloc[0]) >= 20:
                up = float(rs["med_max_ret"].iloc[0])
                dn = float(rs["med_max_dd"].iloc[0])
                basis = f'efter mönstret "{RULE_SV.get(rk, {}).get("titel", rk)}" (median i historiken)'
    if up is None:
        pr = panel_forward_ranges()
        up = pr.get("med_max_ret")
        dn = pr.get("med_max_dd")
    out["upside"] = up
    out["downside"] = dn
    out["range_basis"] = basis
    out["n_rules"] = n_rules
    return out


@st.cache_data(ttl=60)
def e1_experiment() -> pd.DataFrame:
    return q(
        "SELECT experiment_id, name, hypothesis, spec, created_at "
        "FROM experiment WHERE name = 'E1' ORDER BY experiment_id DESC LIMIT 1"
    )


@st.cache_data(ttl=60)
def e1_results(eid: int) -> pd.DataFrame:
    return q(
        "SELECT metric_name, subset, value, ci_low, ci_high, n_obs, n_events, "
        "is_out_of_sample, params FROM experiment_result WHERE experiment_id = ?",
        (eid,),
    )
