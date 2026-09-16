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

from marc.features._common import col_or_nan as _col
from marc.features._common import rolling_accel as _accel
from marc.features._common import rolling_z as _z

_W = 130   # ~26 veckor handelsdagar för baslinjefönstret
_M = 20    # ~4 veckor
_Q = 60    # ~12 veckor


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


def news_sentiment_z(df: pd.DataFrame) -> pd.Series:
    """Z-score av nyckelordsbaserad nyhetssentiment (regel 4: ingen LLM).
    NaN där ingen riktig nyhetsdata finns än (syntetisk källa sätter aldrig
    sentiment) — värmer upp i takt med att verklig historik samlas."""
    s = _col(df, "attn_news_sentiment")
    return _z(s, _W) if s.notna().any() else s
