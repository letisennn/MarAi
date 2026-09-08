"""Feature-set registry.

``compute_feature_frame(df)`` returns a DataFrame indexed like ``df`` with one
column per feature in :data:`FEATURES`. The input ``df`` must be a single
security's daily history, sorted ascending by ``session_date`` and indexed by it,
with columns: ``adj_close``, ``adj_high``, ``adj_low``, ``close_local``,
``open_local``, ``volume``, ``turnover_sek``, ``market_cap_sek``.

Every feature is causal (value at t uses only rows <= t). Enforced by
``tests/test_features_causality.py``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from marc.features import price, volatility, volume

FEATURE_SET_VERSION = "v0.1"

# name -> callable(df) -> Series
FEATURES: dict[str, object] = {
    "ret_1w": lambda d: price.trailing_return(d["adj_close"], 5),
    "ret_1m": lambda d: price.trailing_return(d["adj_close"], 21),
    "ret_3m": lambda d: price.trailing_return(d["adj_close"], 63),
    "ret_6m": lambda d: price.trailing_return(d["adj_close"], 126),
    "ret_12m": lambda d: price.trailing_return(d["adj_close"], 252),
    "dist_52w_high": lambda d: price.dist_52w_high(d["adj_close"], d["adj_high"]),
    "breakout_20d": lambda d: price.breakout_20d(d["adj_close"], d["adj_high"]),
    "gap_freq_20d": lambda d: price.gap_frequency_20d(d["open_local"], d["close_local"]),
    "rvol_5_60": lambda d: volume.relative_volume(d["volume"], 5, 60),
    "rvol_20_200": lambda d: volume.relative_volume(d["volume"], 20, 200),
    "vol_trend_60d": lambda d: volume.volume_trend_60d(d["volume"]),
    "vol_accel": lambda d: volume.volume_acceleration(d["volume"], 5),
    "rv_20d": lambda d: volatility.realized_vol(d["adj_close"], 20),
    "rv_60d": lambda d: volatility.realized_vol(d["adj_close"], 60),
    "vol_expansion": lambda d: volatility.vol_expansion(d["adj_close"], 20, 60),
    "amihud_20d": lambda d: volume.amihud_illiquidity_20d(d["adj_close"], d["turnover_sek"]),
    "log_mktcap": lambda d: np.log(d["market_cap_sek"].where(d["market_cap_sek"] > 0)),
    "log_price_local": lambda d: price.log_price_local(d["close_local"]),
}

FEATURE_NAMES = list(FEATURES)


def compute_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = {name: fn(df) for name, fn in FEATURES.items()}
    return pd.DataFrame(out, index=df.index)
