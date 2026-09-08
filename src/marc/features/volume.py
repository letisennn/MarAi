"""Volume / liquidity features. Causal: value at t uses only rows <= t."""

from __future__ import annotations

import numpy as np
import pandas as pd


def relative_volume(volume: pd.Series, short: int, long: int) -> pd.Series:
    fast = volume.rolling(short, min_periods=max(2, short // 2)).mean()
    slow = volume.rolling(long, min_periods=max(5, long // 3)).mean()
    return fast / slow.replace(0, np.nan)


def volume_acceleration(volume: pd.Series, window: int = 5) -> pd.Series:
    recent = volume.rolling(window, min_periods=window).mean()
    prior = volume.shift(window).rolling(window, min_periods=window).mean()
    return recent / prior.replace(0, np.nan) - 1.0


def _slope(y: np.ndarray) -> float:
    n = len(y)
    if n < 2 or np.any(~np.isfinite(y)):
        return np.nan
    x = np.arange(n, dtype="float64")
    xc = x - x.mean()
    return float((xc * (y - y.mean())).sum() / (xc**2).sum())


def volume_trend_60d(volume: pd.Series, window: int = 60) -> pd.Series:
    logv = np.log(volume.where(volume > 0))
    return logv.rolling(window, min_periods=window * 2 // 3).apply(_slope, raw=True)


def amihud_illiquidity_20d(adj_close: pd.Series, turnover_sek: pd.Series,
                           window: int = 20, scale: float = 1e6) -> pd.Series:
    ret = adj_close.pct_change(fill_method=None).abs()
    daily = (ret / turnover_sek.replace(0, np.nan)) * scale
    return daily.rolling(window, min_periods=window // 2).mean()
