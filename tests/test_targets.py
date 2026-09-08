"""Target construction: base price, gated events, delisting terminal returns."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from marc.targets.forward_returns import DelistInfo, compute_target_frame


def _frame(closes: list[float], turnover: float = 5e7) -> pd.DataFrame:
    idx = pd.bdate_range("2021-01-04", periods=len(closes))
    c = np.array(closes, dtype="float64")
    return pd.DataFrame(
        {"adj_close": c, "adj_high": c, "adj_low": c, "turnover_sek": turnover}, index=idx
    )


def _calendar(df: pd.DataFrame, extra: int = 260) -> pd.DatetimeIndex:
    return pd.bdate_range(df.index[0], periods=len(df) + extra)


def test_flat_then_spike_triggers_50pct_event() -> None:
    closes = [100.0] * 130
    closes[35] = 165.0  # +65% on a liquid day, 31 rows after the t=4 base
    df = _frame(closes)
    out = compute_target_frame(df, _calendar(df))
    # P0 at t=4 is mean of first 5 closes = 100
    assert out.loc[df.index[4], "up_50_60d"] == 1.0
    assert out.loc[df.index[4], "fwd_max_ret_60"] == pytest.approx(0.65, abs=1e-6)
    assert out.loc[df.index[4], "up_50_30d"] == 0.0  # spike is >30 rows out


def test_thin_day_spike_is_gated_out() -> None:
    closes = [100.0] * 130
    closes[20] = 200.0
    df = _frame(closes)
    df.iloc[20, df.columns.get_loc("turnover_sek")] = 10_000.0  # below the gate
    out = compute_target_frame(df, _calendar(df))
    assert out.loc[df.index[4], "up_50_30d"] == 0.0
    assert out.loc[df.index[4], "fwd_max_ret_30"] == pytest.approx(0.0, abs=1e-6)


def test_bankruptcy_terminal_minus_one() -> None:
    df = _frame([100.0] * 40)
    cal = _calendar(df)
    delist = DelistInfo(kind="bankruptcy", date=df.index[-1])
    out = compute_target_frame(df, cal, delist)
    assert out.loc[df.index[4], "fwd_ret_90"] == pytest.approx(-1.0, abs=1e-6)
    assert out.loc[df.index[4], "up_50_90d"] == 0.0
    assert out.loc[df.index[4], "fwd_max_dd_90"] == pytest.approx(-1.0, abs=1e-6)


def test_acquisition_premium_terminal_return() -> None:
    df = _frame([100.0] * 40)
    cal = _calendar(df)
    delist = DelistInfo(kind="acquisition", date=df.index[-1], offer_adj_sek=100.0 * 1.30)
    out = compute_target_frame(df, cal, delist)
    # from an obs a few days before the deal, forward return -> the offer premium
    t = df.index[25]
    assert out.loc[t, "fwd_ret_90"] == pytest.approx(0.30, abs=1e-6)
    assert out.loc[t, "up_25_20d"] == 1.0        # deal (+30%) falls inside 20 rows
    assert out.loc[df.index[4], "up_25_20d"] == 0.0  # too early to see the deal
