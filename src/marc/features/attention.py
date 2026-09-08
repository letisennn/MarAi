"""Kausala attention-features (search / news / forum).

Indata är den dagliga per-bolags-ramen från ``panel.py`` med vecko-attention
forward-fylld till dagsupplösning i kolumnerna ``attn_search``, ``attn_news``,
``attn_forum``. Saknas kolumnerna (t.ex. en pris-bara-körning) returnerar varje
funktion en NaN-serie — aldrig ett fel.

Allt är kausalt: värdet vid t använder bara rader <= t.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_W = 130   # ~26 veckor handelsdagar för baslinjefönstret
_M = 20    # ~4 veckor
_Q = 60    # ~12 veckor


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype="float64")


def _z(s: pd.Series, window: int) -> pd.Series:
    mu = s.rolling(window, min_periods=window // 2).mean()
    sd = s.rolling(window, min_periods=window // 2).std()
    return (s - mu) / sd.replace(0.0, np.nan)


def _accel(s: pd.Series, fast: int, slow: int) -> pd.Series:
    f = s.rolling(fast, min_periods=max(2, fast // 2)).mean()
    sl = s.rolling(slow, min_periods=max(2, slow // 2)).mean()
    return f / sl.replace(0.0, np.nan) - 1.0


def search_level_z(df: pd.DataFrame) -> pd.Series:
    s = _col(df, "attn_search")
    return _z(s, _W) if s.notna().any() else s


def search_accel(df: pd.DataFrame) -> pd.Series:
    s = _col(df, "attn_search")
    return _accel(s, _M, _Q) if s.notna().any() else s


def search_abnormal(df: pd.DataFrame) -> pd.Series:
    s = _col(df, "attn_search")
    if not s.notna().any():
        return s
    z = _z(s, _W)
    out = (z >= 2.0).astype("float64")
    out[z.isna()] = np.nan
    return out


def forum_buzz_z(df: pd.DataFrame) -> pd.Series:
    s = _col(df, "attn_forum")
    return _z(s, _W) if s.notna().any() else s


def forum_accel(df: pd.DataFrame) -> pd.Series:
    s = _col(df, "attn_forum")
    return _accel(s, 10, _Q) if s.notna().any() else s


def news_rate_z(df: pd.DataFrame) -> pd.Series:
    s = _col(df, "attn_news")
    return _z(s, _W) if s.notna().any() else s
