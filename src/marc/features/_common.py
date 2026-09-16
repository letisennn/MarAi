"""Delade hjälpfunktioner för kausala features som är rullande fönster över en
optional/gles kolumn (attention, insider, blankning). Ren aritmetik, ingen I/O.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def col_or_nan(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype="float64")


def rolling_z(s: pd.Series, window: int) -> pd.Series:
    mu = s.rolling(window, min_periods=window // 2).mean()
    sd = s.rolling(window, min_periods=window // 2).std()
    return (s - mu) / sd.replace(0.0, np.nan)


def rolling_accel(s: pd.Series, fast: int, slow: int) -> pd.Series:
    f = s.rolling(fast, min_periods=max(2, fast // 2)).mean()
    sl = s.rolling(slow, min_periods=max(2, slow // 2)).mean()
    return f / sl.replace(0.0, np.nan) - 1.0
