"""E1c — Fama-MacBeth: weekly cross-sectional OLS of forward return on
standardised features; average the weekly coefficients.

v0.1 uses plain average + simple t-stat (mean / se). Newey-West standard errors
are a documented TODO.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from marc.config import get_logger
from marc.features import FEATURE_NAMES
from marc.stats._results import write_result

log = get_logger(__name__)

_TARGET = "fwd_ret_20"
_HOLDOUT_START = pd.Timestamp("2025-01-01")
_MIN_WEEK = 10


def fama_macbeth(con: duckdb.DuckDBPyConnection, experiment_id: int, wide: pd.DataFrame) -> dict:
    small = wide[wide["cap_segment_at_entry"] == "small"]
    disc = small[small["obs_date"] < _HOLDOUT_START]
    feats = [f for f in FEATURE_NAMES if f in disc.columns]
    if _TARGET not in disc.columns or not feats:
        return {"weeks": 0}

    betas: list[np.ndarray] = []
    for _, g in disc.groupby("obs_date"):
        gg = g[feats + [_TARGET]].dropna()
        if len(gg) < _MIN_WEEK:
            continue
        x = gg[feats].to_numpy(dtype="float64")
        x = (x - x.mean(0)) / np.where(x.std(0) > 0, x.std(0), 1.0)
        x = np.column_stack([np.ones(len(x)), x])
        y = gg[_TARGET].to_numpy(dtype="float64")
        try:
            beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        except np.linalg.LinAlgError:
            continue
        betas.append(beta)

    if len(betas) < _MIN_WEEK:
        log.info("E1c Fama-MacBeth: only %d usable weeks, skipping", len(betas))
        return {"weeks": len(betas)}

    B = np.vstack(betas)
    mean = B.mean(0)
    se = B.std(0, ddof=1) / np.sqrt(len(B))
    names = ["intercept"] + feats
    for i, nm in enumerate(names):
        t = mean[i] / se[i] if se[i] > 0 else np.nan
        write_result(con, experiment_id, f"fm_beta:{nm}:{_TARGET}", float(mean[i]),
                     subset={"split": "discovery", "feature": nm, "target": _TARGET},
                     ci_low=float(mean[i] - 1.96 * se[i]), ci_high=float(mean[i] + 1.96 * se[i]),
                     n_obs=len(B),
                     params={"t_stat": None if t != t else round(float(t), 3)})
    log.info("E1c Fama-MacBeth: %d weeks", len(B))
    return {"weeks": len(B)}
