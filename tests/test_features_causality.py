"""Every feature must be causal: appending future rows cannot change past values,
and a feature computed on a truncated history equals the same row on the full
history.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from marc.features import FEATURE_NAMES, compute_feature_frame


def _synthetic_frame(n: int = 900, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n)
    close = 40 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, n)))
    vol = rng.lognormal(11, 0.6, n)
    df = pd.DataFrame(
        {
            "adj_close": close,
            "adj_high": close * (1 + np.abs(rng.normal(0, 0.01, n))),
            "adj_low": close * (1 - np.abs(rng.normal(0, 0.01, n))),
            "close_local": close,
            "open_local": close * (1 + rng.normal(0, 0.004, n)),
            "volume": vol,
            "turnover_sek": vol * close,
            "market_cap_sek": close * 20e6,
        },
        index=idx,
    )
    return df


def test_appending_future_rows_does_not_change_past_features() -> None:
    df = _synthetic_frame()
    full = compute_feature_frame(df)
    truncated = compute_feature_frame(df.iloc[:-40])

    common = truncated.index
    a = full.loc[common, FEATURE_NAMES]
    b = truncated.loc[common, FEATURE_NAMES]
    pd.testing.assert_frame_equal(a, b, check_dtype=False, rtol=1e-9, atol=1e-9)


@pytest.mark.parametrize("cut", [300, 500, 750, 880])
def test_pointwise_equals_full_history(cut: int) -> None:
    df = _synthetic_frame()
    full_row = compute_feature_frame(df).iloc[cut]
    trunc_row = compute_feature_frame(df.iloc[: cut + 1]).iloc[-1]
    for name in FEATURE_NAMES:
        x, y = full_row[name], trunc_row[name]
        if pd.isna(x) and pd.isna(y):
            continue
        assert x == pytest.approx(y, rel=1e-9, abs=1e-9), name
