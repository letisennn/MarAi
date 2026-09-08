"""Price features. Every function is causal: value at t uses only rows <= t."""

from __future__ import annotations

import numpy as np
import pandas as pd


def trailing_return(adj_close: pd.Series, n: int) -> pd.Series:
    return adj_close.pct_change(n, fill_method=None)


def dist_52w_high(adj_close: pd.Series, adj_high: pd.Series, window: int = 252) -> pd.Series:
    roll_high = adj_high.rolling(window, min_periods=60).max()
    return adj_close / roll_high - 1.0


def breakout_20d(adj_close: pd.Series, adj_high: pd.Series, window: int = 20) -> pd.Series:
    prior_high = adj_high.shift(1).rolling(window, min_periods=window // 2).max()
    return (adj_close > prior_high).astype("float64").where(prior_high.notna())


def gap_frequency_20d(open_local: pd.Series, close_local: pd.Series,
                      window: int = 20, thresh: float = 0.03) -> pd.Series:
    gap = (open_local / close_local.shift(1) - 1.0).abs()
    return (gap > thresh).astype("float64").rolling(window, min_periods=window // 2).mean()


def log_price_local(close_local: pd.Series) -> pd.Series:
    return np.log(close_local.where(close_local > 0))
