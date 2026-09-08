"""Volatility features. Causal: value at t uses only rows <= t."""

from __future__ import annotations

import numpy as np
import pandas as pd

_ANNUALISE = np.sqrt(252.0)


def realized_vol(adj_close: pd.Series, window: int) -> pd.Series:
    logret = np.log(adj_close.where(adj_close > 0)).diff()
    return logret.rolling(window, min_periods=max(5, window * 2 // 3)).std() * _ANNUALISE


def vol_expansion(adj_close: pd.Series, short: int = 20, long: int = 60) -> pd.Series:
    return realized_vol(adj_close, short) / realized_vol(adj_close, long)
