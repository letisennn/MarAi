"""E1b — univariate: weekly cross-sectional quintile sorts + rank IC.

For each feature x forward-return horizon: weekly Spearman IC (mean + t-stat +
block-bootstrap CI), pooled quintile mean forward return, Q5-Q1 spread. Plus
``P(event | top-quintile of feature)`` vs the base rate. Run separately on the
discovery period and the untouched holdout.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from marc.config import get_logger, targets_config
from marc.features import FEATURE_NAMES
from marc.stats._results import write_result

log = get_logger(__name__)

_RET_HORIZONS = [20, 60, 90]
_HOLDOUT_START = pd.Timestamp("2025-01-01")
_N_QUINTILES = 5
_BOOT = 300
_BLOCK = 8


def _weekly_ic(df: pd.DataFrame, feat: str, tgt: str) -> pd.Series:
    out = {}
    for d, g in df.groupby("obs_date"):
        gg = g[[feat, tgt]].dropna()
        if len(gg) >= 8 and gg[feat].nunique() > 3:
            out[d] = gg[feat].rank().corr(gg[tgt].rank())
    return pd.Series(out, dtype="float64").dropna()


def _block_boot_ci(x: np.ndarray, reps: int = _BOOT, block: int = _BLOCK) -> tuple[float, float]:
    if len(x) < block * 2:
        return (np.nan, np.nan)
    n = len(x)
    n_blocks = int(np.ceil(n / block))
    rng = np.random.default_rng(12345)
    means = np.empty(reps)
    starts_pool = np.arange(0, n - block + 1)
    for r in range(reps):
        starts = rng.choice(starts_pool, size=n_blocks, replace=True)
        sample = np.concatenate([x[s : s + block] for s in starts])[:n]
        means[r] = sample.mean()
    return (float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975)))


def _quintile_means(df: pd.DataFrame, feat: str, tgt: str) -> list[float] | None:
    weekly = []
    for _, g in df.groupby("obs_date"):
        gg = g[[feat, tgt]].dropna()
        if len(gg) < _N_QUINTILES * 2 or gg[feat].nunique() < _N_QUINTILES:
            continue
        q = pd.qcut(gg[feat].rank(method="first"), _N_QUINTILES, labels=False)
        weekly.append(gg[tgt].groupby(q).mean())
    if not weekly:
        return None
    m = pd.concat(weekly, axis=1).mean(axis=1)
    return [float(m.get(i, np.nan)) for i in range(_N_QUINTILES)]


def _run_split(con, eid, df: pd.DataFrame, oos: bool, tag: str) -> None:
    events = [e["name"] for e in targets_config()["events"]]
    for feat in FEATURE_NAMES:
        if feat not in df.columns:
            continue
        for h in _RET_HORIZONS:
            tgt = f"fwd_ret_{h}"
            if tgt not in df.columns:
                continue
            ic = _weekly_ic(df, feat, tgt)
            if len(ic) >= 10:
                m = float(ic.mean())
                t = m / (ic.std(ddof=1) / np.sqrt(len(ic))) if ic.std(ddof=1) > 0 else np.nan
                lo, hi = _block_boot_ci(ic.to_numpy())
                write_result(con, eid, f"ic_mean:{feat}:{tgt}", m,
                             subset={"split": tag, "feature": feat, "target": tgt},
                             ci_low=lo, ci_high=hi, n_obs=len(ic), is_out_of_sample=oos,
                             params={"t_stat": None if t != t else round(float(t), 3)})
            qm = _quintile_means(df, feat, tgt)
            if qm and not any(np.isnan(qm[i]) for i in (0, _N_QUINTILES - 1)):
                write_result(con, eid, f"q5_q1_spread:{feat}:{tgt}", qm[-1] - qm[0],
                             subset={"split": tag, "feature": feat, "target": tgt,
                                     "q_means": [round(v, 4) for v in qm]},
                             is_out_of_sample=oos)

        # feature top-quintile vs event base rate
        for ev in events:
            if ev not in df.columns:
                continue
            sub = df[[feat, ev, "obs_date"]].dropna()
            if len(sub) < 200:
                continue
            top = []
            for _, g in sub.groupby("obs_date"):
                if g[feat].nunique() < _N_QUINTILES:
                    continue
                thr = g[feat].quantile(0.8)
                top.append(g[g[feat] >= thr])
            if not top:
                continue
            topdf = pd.concat(top)
            base = float(sub[ev].mean())
            cond = float(topdf[ev].mean())
            lift = cond / base if base > 0 else np.nan
            write_result(con, eid, f"lift_top_quintile:{feat}:{ev}", lift,
                         subset={"split": tag, "feature": feat, "event": ev,
                                 "p_cond": round(cond, 4), "p_base": round(base, 4)},
                         n_obs=len(topdf), n_events=int(topdf[ev].sum()), is_out_of_sample=oos)


def univariate_sweep(con: duckdb.DuckDBPyConnection, experiment_id: int, wide: pd.DataFrame) -> dict:
    small = wide[wide["cap_segment_at_entry"] == "small"].copy()
    disc = small[small["obs_date"] < _HOLDOUT_START]
    hold = small[small["obs_date"] >= _HOLDOUT_START]
    log.info("E1b univariate: discovery n=%d, holdout n=%d", len(disc), len(hold))
    _run_split(con, experiment_id, disc, oos=False, tag="discovery")
    if len(hold) > 500:
        _run_split(con, experiment_id, hold, oos=True, tag="holdout")
    return {"discovery_obs": len(disc), "holdout_obs": len(hold)}
