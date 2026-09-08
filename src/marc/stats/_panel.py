"""Shared: load the wide analysis panel (observation + features + targets)."""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from marc.config import universe_config
from marc.features import FEATURE_SET_VERSION


def load_wide(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    name = universe_config()["universe_name"]
    obs = con.execute(
        """
        SELECT o.obs_id, o.security_id, o.obs_date, o.cap_segment_at_entry, o.market_cap_sek,
               s.country
        FROM observation o JOIN security s USING (security_id)
        WHERE o.universe_name = ? AND o.feature_set_version = ?
        """,
        [name, FEATURE_SET_VERSION],
    ).df()
    if obs.empty:
        return obs
    feat = con.execute("SELECT obs_id, feature_name, value FROM feature_panel").df()
    tgt = con.execute("SELECT obs_id, target_name, value FROM target_panel").df()
    fw = feat.pivot(index="obs_id", columns="feature_name", values="value")
    tw = tgt.pivot(index="obs_id", columns="target_name", values="value")

    wide = obs.set_index("obs_id").join(fw).join(tw)
    wide["obs_date"] = pd.to_datetime(wide["obs_date"])
    wide["year"] = wide["obs_date"].dt.year
    return wide


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))
