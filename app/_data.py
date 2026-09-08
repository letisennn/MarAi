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

# Mörkt tema för alla Plotly-diagram (Streamlit-temat sätts i .streamlit/config.toml).
# Genomskinlig bakgrund så figurerna smälter in i appens ytor.
try:  # pragma: no cover - ren presentationsinställning
    import plotly.graph_objects as _go
    import plotly.io as _pio

    _pio.templates["marc_dark"] = _go.layout.Template(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e6e6e6"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.16)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.16)"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
    )
    _pio.templates.default = "plotly_dark+marc_dark"
except Exception:  # noqa: BLE001
    pass

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


# --------------------------------------------------------------------------- #
# tolkning i klartext — en färdig slutsats per bolag
# --------------------------------------------------------------------------- #


def _g(feats: dict, name: str):
    v = feats.get(name)
    return None if _is_missing(v) else float(v)


def _pct(v, plus: bool = True) -> str:
    if v is None:
        return "–"
    return f"{v * 100:+.0f} %" if plus else f"{v * 100:.0f} %"


def _ctx_1y(fhist: pd.DataFrame, name: str, value) -> str:
    """Var ligger dagens värde mot bolagets senaste ~52 veckor?"""
    if value is None or fhist.empty or name not in fhist.columns:
        return ""
    s = pd.to_numeric(fhist[name], errors="coerce").dropna().tail(52)
    if len(s) < 12:
        return ""
    pct = float((s < value).mean())
    if pct >= 0.92:
        return "det högsta på ett år"
    if pct <= 0.08:
        return "det lägsta på ett år"
    if pct >= 0.75:
        return "högt för bolaget"
    if pct <= 0.25:
        return "lågt för bolaget"
    return ""


@st.cache_data(ttl=60)
def verdict(sid: int, weeks: int = 8) -> dict:
    """En färdigtolkad slutsats för ett bolag: kategori, en mening, varför, emot,
    och den siffra som betyder något. Preliminär och ovaliderad — regelvikter och
    trösklar är handsatta. Beskriver nuläget mot historisk frekvens, ingen prognos.
    """
    obs_date, feats = security_features_latest(sid)
    if not feats:
        return {
            "kategori": "Utanför universumet",
            "ikon": "•",
            "slutsats": (
                "Bolaget har inte funnits i universumet under perioden (för litet, "
                "för lågt handlat, för kort historik, uppköpt eller i konkurs). "
                "Inga mätningar att tolka — bara kurshistoriken längre ner."
            ),
            "darfor": [],
            "emot": [],
            "nyckeltal": None,
            "as_of": obs_date,
        }

    fhist = security_feature_history(sid)
    hist = security_signal_history(sid)
    stats = rule_outcome_stats()
    brm = base_rate_map()
    base90 = brm.get("90d")

    r1m, r3m, r12m = _g(feats, "ret_1m"), _g(feats, "ret_3m"), _g(feats, "ret_12m")
    dist = _g(feats, "dist_52w_high")
    rvol = _g(feats, "rvol_5_60")
    vacc = _g(feats, "vol_accel")
    rv20 = _g(feats, "rv_20d")
    brk = _g(feats, "breakout_20d")
    sacc, facc = _g(feats, "search_accel"), _g(feats, "forum_accel")
    slz = _g(feats, "search_level_z")

    # vilka regler lyste de senaste `weeks` veckorna
    recent_rules: list[str] = []
    last_fire = None
    if not hist.empty and obs_date is not None:
        rd = q("SELECT DISTINCT obs_date FROM observation ORDER BY obs_date DESC LIMIT ?", (weeks,))
        cutoff = pd.to_datetime(rd["obs_date"]).min() if not rd.empty else None
        h = hist.assign(_d=pd.to_datetime(hist["as_of_date"]))
        if cutoff is not None:
            h = h[h["_d"] >= cutoff]
        recent_rules = list(dict.fromkeys(h.sort_values("_d")["rule"].tolist()))
        if not h.empty:
            last_fire = h["_d"].max()

    def _rule_number(rk: str) -> str | None:
        if stats.empty:
            return None
        rs = stats[(stats["rule"] == rk) & (stats["horizon"] == "90d")]
        if rs.empty or int(rs["n"].iloc[0]) < 20:
            return None
        hit = float(rs["hit_rate"].iloc[0])
        titel = RULE_SV.get(rk, {}).get("titel", rk)
        base_txt = f" (normalt {_pct(base90, plus=False)})" if base90 else ""
        return (
            f'När mönstret "{titel}" lyst tidigare har en uppgång på minst +50 % inom '
            f"~4 månader följt i {hit * 100:.0f} % av fallen{base_txt}. "
            "Beskrivande historik, inte en prognos."
        )

    generic_number = (
        f"Referens: ett litet bolag i universumet når +50 % inom ~4 månader i "
        f"{_pct(base90, plus=False)} av alla veckor. Ingen bekräftad signal höjer "
        "oddsen för det här bolaget just nu."
        if base90 else None
    )

    def vol_line() -> str | None:
        if rvol is None:
            return None
        c = _ctx_1y(fhist, "rvol_5_60", rvol)
        tail = f", {c}" if c else ""
        trend = ""
        if vacc is not None:
            trend = " och stigande" if vacc > 0 else " och fallande" if vacc < 0 else ""
        return f"Handeln ligger {pct_vs_normal(rvol)}{trend}{tail}."

    def dist_line() -> str | None:
        if dist is None:
            return None
        if dist >= -0.03:
            return "Kursen står vid sitt högsta på 52 veckor."
        if dist >= -0.10:
            return f"Kursen är {_pct(abs(dist), plus=False)} under årshögsta — inom räckhåll."
        if dist >= -0.30:
            return f"Kursen är {_pct(abs(dist), plus=False)} under årshögsta."
        return f"Kursen är långt under årshögsta ({_pct(abs(dist), plus=False)} ned)."

    def trend_line() -> str | None:
        if r3m is None:
            return None
        parts = [f"{_pct(r3m)} på 3 månader"]
        if r12m is not None:
            parts.append(f"{_pct(r12m)} på 12 månader")
        return "Kursutveckling: " + ", ".join(parts) + "."

    def attn_line() -> str | None:
        bits = []
        if sacc is not None and sacc >= 0.12:
            bits.append(f"sökintresset ökar ({_pct(sacc)} mot en månad sedan)")
        if facc is not None and facc >= 0.12:
            bits.append(f"forumaktiviteten ökar ({_pct(facc)})")
        if slz is not None and slz >= 1.5 and not bits:
            bits.append("sökintresset ligger högt för bolaget")
        if not bits:
            return None
        return "Uppmärksamhet: " + " och ".join(bits) + ". (Syntetisk attention-data.)"

    vol_rising = (vacc is not None and vacc > 0) or (rvol is not None and rvol >= 1.2)
    exploded_now = (rvol is not None and rvol >= 2.5 and r1m is not None and r1m >= 0.15)
    calm_price = r1m is not None and -0.06 <= r1m <= 0.15

    # ---- beslutsträd, första träff vinner --------------------------------
    kat = ikon = slutsats = None
    darfor: list[str] = []
    emot: list[str] = []
    nyckeltal = generic_number

    if ("rule1" in recent_rules or "rule2" in recent_rules) or exploded_now:
        kat, ikon = "Utbrott pågår", "🚀"
        slutsats = (
            "Rör sig kraftigt just nu på hög volym — utbrottet har redan börjat. "
            "Det här är inte ett tidigt läge."
        )
        darfor = [x for x in (
            f"Kursen är {_pct(r1m)} den senaste månaden." if r1m is not None else None,
            vol_line(),
            "Ny 20-dagarshögsta noterad den här veckan." if brk and brk >= 0.5 else None,
            dist_line(),
        ) if x]
        emot = [
            "Går man in mitt i ett utbrott är en stor del av rörelsen ofta redan gjord; "
            "bakslag på 15–30 % är vanliga.",
        ]
        if r3m is not None and r3m >= 0.6:
            emot.append(f"Bolaget har redan gått {_pct(r3m)} på tre månader.")
        rk = "rule1" if "rule1" in recent_rules else ("rule2" if "rule2" in recent_rules else None)
        nyckeltal = (_rule_number(rk) if rk else None) or generic_number

    elif dist is not None and dist >= -0.06 and (r3m or 0) > 0 and vol_rising and (r1m or 0) < 0.20:
        kat, ikon = "Nära utbrott", "⚡"
        slutsats = (
            "Står precis under årshögsta med stigande handel — ett klassiskt läge strax "
            "före ett utbrott. Inget utbrott är bekräftat än."
        )
        darfor = [x for x in (dist_line(), trend_line(), vol_line(), attn_line()) if x]
        emot = [
            "Nära årshögsta vänder ungefär lika ofta ner som det bryter upp. Utan att "
            "volymen och intresset fortsätter öka är det bara en prisnivå.",
        ]
        nyckeltal = _rule_number("rule3") or generic_number

    elif vol_rising and calm_price and dist is not None and -0.38 <= dist <= -0.07:
        kat, ikon = "Under uppbyggnad", "🌱"
        slutsats = (
            "Handeln tilltar medan kursen fortfarande är lugn och en bit under årshögsta "
            "— mönstret som ibland föregår en större rörelse. Obevisat, en hypotes vi testar."
        )
        darfor = [x for x in (
            vol_line(),
            f"Kursen är samtidigt lugn ({_pct(r1m)} senaste månaden)." if r1m is not None else None,
            dist_line(),
            attn_line(),
        ) if x]
        emot = [
            "Ökad volym utan att kursen följer med leder oftast ingenstans. Det här är "
            "inte en bekräftad signal — det är ett mönster under test.",
        ]
        nyckeltal = generic_number

    elif r3m is not None and r3m >= 0.6 and dist is not None and dist >= -0.04:
        kat, ikon = "Överhettad", "🔥"
        slutsats = (
            f"Har redan gått {_pct(r3m)} på tre månader och står vid toppen. Ett nytt "
            "köp härifrån har historiskt sämre odds än risken."
        )
        darfor = [x for x in (
            trend_line(),
            "Kursen står vid 52-veckors högsta.",
            f"Rörligheten är hög ({_pct(rv20, plus=False)} i årstakt)." if rv20 is not None else None,
        ) if x]
        emot = [
            "Starka trender pågår ofta längre än man tror. Det här är ingen säljsignal — "
            "bara att ett nytt köp på den här nivån har dålig historik.",
        ]
        nyckeltal = generic_number

    elif r12m is not None and r12m <= -0.30 and (r1m or 0) > 0.05 and vol_rising:
        kat, ikon = "Utbombad — möjlig vändning", "🩹"
        slutsats = (
            "Har fallit tungt på ett år, men den senaste månaden är positiv på stigande "
            "volym — ett tidigt tecken på möjlig vändning. Osäkert."
        )
        darfor = [x for x in (
            f"Ned {_pct(r12m)} på 12 månader men {_pct(r1m)} den senaste månaden." if r1m is not None else None,
            vol_line(),
            dist_line(),
            attn_line(),
        ) if x]
        emot = [
            "De flesta studsar i en nedtrend rinner ut i sanden. Vändningen är bekräftad "
            "först när högre bottnar och toppar byggs.",
        ]
        nyckeltal = generic_number

    elif r3m is not None and r3m <= -0.15 and (r1m or 0) <= 0 and (dist or 0) <= -0.25:
        kat, ikon = "Fallande — ingen vändning", "📉"
        slutsats = (
            "Nedtrend utan tecken på vändning: fallande kurs, ingen ökad köpvolym, "
            "långt under årshögsta."
        )
        darfor = [x for x in (trend_line(), dist_line(), vol_line()) if x]
        emot = [
            "Utbombade bolag kan vända snabbt när humöret skiftar — bevaka för stigande "
            "volym som första tecken.",
        ]
        nyckeltal = generic_number

    else:
        kat, ikon = "Ingen signal", "•"
        slutsats = (
            "Rör sig i sidled utan något av de mönster vi letar efter. Inget att agera på."
        )
        darfor = [x for x in (trend_line(), vol_line(), dist_line()) if x]
        emot = ["Bevaka om handeln börjar ticka upp — det är oftast det första som händer."]
        nyckeltal = generic_number

    return {
        "kategori": kat,
        "ikon": ikon,
        "slutsats": slutsats,
        "darfor": darfor,
        "emot": emot,
        "nyckeltal": nyckeltal,
        "as_of": obs_date,
        "fired_recently": recent_rules,
        "last_fire": None if last_fire is None else last_fire.date(),
    }


@st.cache_data(ttl=60)
def movers(window: str = "1m", segment: str = "small", limit: int = 25) -> pd.DataFrame:
    """Största kursrörelserna i universumet över ett fönster, störst först.

    window: '1w' -> ret_1w, '1m' -> ret_1m, '3m' -> ret_3m, '12m' -> ret_12m.
    Visar bolagets senaste observation. Beskrivande, ingen prognos.
    """
    feat = {"1w": "ret_1w", "1m": "ret_1m", "3m": "ret_3m", "12m": "ret_12m"}.get(window, "ret_1m")
    sql = f"""
    WITH last_obs AS (SELECT security_id, max(obs_date) AS obs_date FROM observation GROUP BY 1),
    orw AS (
        SELECT o.security_id, o.obs_id, o.obs_date, o.cap_segment_at_entry AS segment
        FROM observation o JOIN last_obs l
          ON l.security_id = o.security_id AND l.obs_date = o.obs_date
    ),
    f AS (
        SELECT obs_id,
            max(value) FILTER (WHERE feature_name = '{feat}')       AS move,
            max(value) FILTER (WHERE feature_name = 'ret_1m')       AS ret_1m,
            max(value) FILTER (WHERE feature_name = 'ret_3m')       AS ret_3m,
            max(value) FILTER (WHERE feature_name = 'dist_52w_high') AS dist_52w_high,
            max(value) FILTER (WHERE feature_name = 'rvol_5_60')    AS rvol_5_60,
            max(value) FILTER (WHERE feature_name = 'vol_accel')    AS vol_accel
        FROM feature_panel WHERE obs_id IN (SELECT obs_id FROM orw)
        GROUP BY obs_id
    )
    SELECT s.security_id, s.name, s.sector, orw.segment, orw.obs_date,
           f.move, f.ret_1m, f.ret_3m, f.dist_52w_high, f.rvol_5_60, f.vol_accel
    FROM orw JOIN security s USING (security_id) JOIN f ON f.obs_id = orw.obs_id
    WHERE f.move IS NOT NULL
    ORDER BY f.move DESC
    """
    df = q(sql)
    if segment in ("small", "mid"):
        df = df[df["segment"] == segment]
    return df.head(limit).reset_index(drop=True)


@st.cache_data(ttl=60)
def move_precursor(sid: int, weeks_before: int = 4) -> pd.DataFrame:
    """Hur såg mätvärdena ut veckorna INNAN bolagets senaste observation.

    Svarar på "fanns det något att se i förväg". Tar de sista `weeks_before`+1
    observationerna och visar volym, avstånd till årshögsta, kursutveckling och
    om något förregistrerat mönster lyste den veckan.
    """
    fh = security_feature_history(sid)
    if fh.empty:
        return pd.DataFrame()
    cols = [c for c in ["obs_date", "ret_1w", "ret_1m", "rvol_5_60", "vol_accel",
                        "dist_52w_high", "search_accel", "forum_accel"] if c in fh.columns]
    tail = fh[cols].tail(weeks_before + 1).copy()
    sh = security_signal_history(sid)
    fired = {}
    if not sh.empty:
        s = sh.assign(_d=pd.to_datetime(sh["as_of_date"]))
        for d, grp in s.groupby("_d"):
            fired[pd.Timestamp(d).normalize()] = ", ".join(sorted(grp["rule"].unique()))
    tail["monster_lyste"] = tail["obs_date"].dt.normalize().map(fired).fillna("—")
    return tail.reset_index(drop=True)


@st.cache_data(ttl=60)
def historical_breakouts(min_fwd_20: float = 0.25) -> dict:
    """Panelbrett: av alla veckoobservationer som FÖLJDES av en uppgång på minst
    ``min_fwd_20`` inom 20 handelsdagar — hur ofta syntes förhöjd volym eller
    stigande handel redan samma vecka? Rent beskrivande, svarar på om det fanns
    något mätbart att se i förväg.
    """
    df = q(
        """
        WITH mv AS (
            SELECT o.obs_id
            FROM observation o JOIN target_panel tp USING (obs_id)
            WHERE o.cap_segment_at_entry = 'small'
              AND tp.target_name = 'fwd_ret_20' AND tp.value >= ?
        ),
        f AS (
            SELECT obs_id,
                max(value) FILTER (WHERE feature_name = 'rvol_5_60') AS rvol,
                max(value) FILTER (WHERE feature_name = 'vol_accel') AS vacc,
                max(value) FILTER (WHERE feature_name = 'dist_52w_high') AS dist
            FROM feature_panel WHERE obs_id IN (SELECT obs_id FROM mv)
            GROUP BY obs_id
        )
        SELECT
            count(*)                                                  AS n,
            avg(CASE WHEN rvol >= 1.5 THEN 1.0 ELSE 0.0 END)          AS p_high_vol,
            avg(CASE WHEN vacc > 0 THEN 1.0 ELSE 0.0 END)             AS p_vol_rising,
            avg(CASE WHEN dist >= -0.10 THEN 1.0 ELSE 0.0 END)        AS p_near_high
        FROM f
        """,
        (min_fwd_20,),
    )
    base = q(
        """
        WITH f AS (
            SELECT obs_id,
                max(value) FILTER (WHERE feature_name = 'rvol_5_60') AS rvol
            FROM feature_panel
            WHERE obs_id IN (SELECT obs_id FROM observation WHERE cap_segment_at_entry = 'small')
            GROUP BY obs_id
        )
        SELECT avg(CASE WHEN rvol >= 1.5 THEN 1.0 ELSE 0.0 END) AS p_high_vol_all FROM f
        """
    )
    out = {} if df.empty else df.iloc[0].to_dict()
    out["p_high_vol_all"] = None if base.empty else float(base.iloc[0]["p_high_vol_all"])
    out["threshold"] = min_fwd_20
    return out
