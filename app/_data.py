"""Shared read-only data access for the Streamlit app.

The app NEVER writes. All research logic lives in the ``marc`` package; this
module only queries ``data/marc.duckdb`` and caches the results.
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

from marc.config import get_settings  # noqa: E402


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
def securities() -> pd.DataFrame:
    return q(
        """
        SELECT security_id, isin, name, country, currency, base_listing_mic AS mic,
               sector, status, status_date
        FROM security ORDER BY name
        """
    )


@st.cache_data(ttl=60)
def universe_name() -> str:
    from marc.config import universe_config

    return universe_config()["universe_name"]


@st.cache_data(ttl=60)
def members_asof(on_date) -> pd.DataFrame:
    return q(
        """
        SELECT s.name, s.country, s.sector, s.status,
               m.valid_from, m.valid_to,
               pc.market_cap_sek, pc.turnover_sek
        FROM universe_membership m
        JOIN security s USING (security_id)
        LEFT JOIN price_clean pc
               ON pc.security_id = m.security_id
              AND pc.session_date = (
                  SELECT max(session_date) FROM price_clean
                  WHERE security_id = m.security_id AND session_date <= ?
              )
        WHERE m.universe_name = ?
          AND m.valid_from <= ?
          AND (m.valid_to IS NULL OR m.valid_to > ?)
        ORDER BY pc.market_cap_sek DESC NULLS LAST
        """,
        (on_date, universe_name(), on_date, on_date),
    )


@st.cache_data(ttl=60)
def obs_date_bounds() -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    df = q("SELECT min(obs_date) lo, max(obs_date) hi FROM observation")
    if df.empty or pd.isna(df.loc[0, "lo"]):
        return (None, None)
    return (pd.Timestamp(df.loc[0, "lo"]), pd.Timestamp(df.loc[0, "hi"]))


@st.cache_data(ttl=60)
def pipeline_status() -> pd.DataFrame:
    tables = [
        "security", "price_daily", "corporate_action", "universe_membership",
        "observation", "feature_panel", "target_panel", "experiment_result",
        "signal_log", "signal_outcome",
    ]
    rows = []
    con = get_con()
    for t in tables:
        try:
            n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        except Exception:  # noqa: BLE001
            n = None
        rows.append({"table": t, "rows": n})
    return pd.DataFrame(rows)
