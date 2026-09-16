"""Kausala features från insiderhandel (FI PDMR) och blankning (FI blankningsregister).

Indata (från ``panel.py``): ``insider_net_buy_90d_sek`` (rullande 90-dagars
nettobelopp, redan kausalt beräknat på publiceringsdatum — inte transaktions-
datum, se ``panel._attach_insider_short``) och ``short_interest_pct`` (senast
kända nivå). Saknas kolumnerna (inga manuella exporter inlästa) returnerar
varje funktion en NaN-serie — aldrig ett fel, precis som attention-features.
"""

from __future__ import annotations

import pandas as pd

from marc.features._common import col_or_nan as _col
from marc.features._common import rolling_accel as _accel
from marc.features._common import rolling_z as _z

_W = 130
_M = 20
_Q = 60


def insider_net_buy_z(df: pd.DataFrame) -> pd.Series:
    s = _col(df, "insider_net_buy_90d_sek")
    return _z(s, _W) if s.notna().any() else s


def short_interest_level(df: pd.DataFrame) -> pd.Series:
    return _col(df, "short_interest_pct")


def short_interest_accel(df: pd.DataFrame) -> pd.Series:
    s = _col(df, "short_interest_pct")
    return _accel(s, _M, _Q) if s.notna().any() else s
