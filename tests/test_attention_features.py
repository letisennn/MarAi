"""Attention-features: kausalitet + graceful no-op när kolumner saknas."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from marc.features.registry import compute_feature_frame

_ATTN = ["search_level_z", "search_accel", "search_abnormal",
         "forum_buzz_z", "forum_accel", "news_rate_z"]


def _frame(n: int = 600, *, attention: bool) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2020-01-01", periods=n)
    close = 50 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, n)))
    df = pd.DataFrame(
        {
            "adj_close": close,
            "adj_high": close * 1.01,
            "adj_low": close * 0.99,
            "close_local": close,
            "open_local": close,
            "volume": rng.integers(1e4, 1e6, n).astype(float),
            "turnover_sek": close * rng.integers(1e4, 1e6, n),
            "market_cap_sek": close * 1e7,
        },
        index=idx,
    )
    if attention:
        wk = np.repeat(rng.uniform(5, 60, n // 5 + 1), 5)[:n]
        df["attn_search"] = np.clip(wk + rng.normal(0, 3, n), 0, 100)
        df["attn_forum"] = np.clip(wk / 10 + rng.normal(0, 1, n), 0, None)
        df["attn_news"] = np.clip(wk / 25 + rng.normal(0, 0.5, n), 0, None)
    return df


def test_attention_features_noop_without_columns() -> None:
    out = compute_feature_frame(_frame(attention=False))
    for c in _ATTN:
        assert c in out.columns
        assert out[c].isna().all()


def test_attention_features_are_causal() -> None:
    full = _frame(n=600, attention=True)
    cut = 450
    past = compute_feature_frame(full.iloc[:cut])
    with_future = compute_feature_frame(full)[_ATTN].iloc[:cut]
    assert_frame_equal(past[_ATTN], with_future, check_exact=False, atol=1e-9)


def test_attention_features_have_signal_when_present() -> None:
    out = compute_feature_frame(_frame(n=600, attention=True))
    assert out["search_level_z"].notna().sum() > 100
    assert out["search_abnormal"].dropna().isin([0.0, 1.0]).all()
