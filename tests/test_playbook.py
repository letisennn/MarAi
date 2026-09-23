"""E1e playbook: utfall räknas från KÖPKURSEN (stängning dag t), inte från E1:s
P0 (5-dagarsmedel) — annars överdrivs vinsten efter en kraftig uppgång (Jonas,
2026-09-23: "vad innebär det för oss som vill köpa")."""

from __future__ import annotations

import numpy as np
import pandas as pd

from marc.stats.playbook import _entry_metrics_for, _metrics, _verdict_labels


def _px(closes: list[float]) -> pd.DataFrame:
    idx = pd.bdate_range("2026-01-05", periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({
        "adj_close": c, "adj_high": c * 1.01, "adj_low": c * 0.99,
        "turnover_sek": pd.Series(1_000_000.0, index=idx),
    })


def test_entry_return_is_measured_from_the_close_at_t() -> None:
    df = _px([100.0] * 5 + [110.0] * 10)
    em = _entry_metrics_for(df, (5,), gate_abs=250_000, gate_frac=0.5)
    # t = dag 0: 100 -> 110 fem dagar senare
    assert em["e_ret_5"].iloc[0] == np.float64(110.0 / 100.0 - 1.0)


def test_entry_basis_is_not_inflated_by_a_recent_run_up() -> None:
    """Efter en uppgång ligger 5-dagarsmedelvärdet UNDER stängningskursen — en
    P0-baserad avkastning hade räknat mellanskillnaden som framtida vinst."""
    df = _px([100.0, 104.0, 108.0, 112.0, 116.0, 120.0, 120.0, 120.0, 120.0, 120.0, 120.0])
    p0 = df["adj_close"].rolling(5).mean()
    em = _entry_metrics_for(df, (5,), gate_abs=250_000, gate_frac=0.5)
    t = 5  # köper på stängningen 120
    p0_based = df["adj_close"].iloc[t + 5] / p0.iloc[t] - 1.0
    assert p0_based > 0.05                      # P0 säger +9 % ...
    assert abs(em["e_ret_5"].iloc[t]) < 1e-9    # ... köparen fick 0 %


def test_drawdown_and_best_point_are_relative_to_entry() -> None:
    # 25 lugna dagar först — omsättningsgrindens 60-dagarsmedian kräver minst 20
    df = _px([100.0] * 25 + [100.0, 90.0, 120.0, 100.0, 100.0, 100.0, 100.0])
    em = _entry_metrics_for(df, (4,), gate_abs=250_000, gate_frac=0.5)
    t = 25
    assert em["e_maxdd_4"].iloc[t] < -0.10      # lägsta 89,1 mot köpkurs 100
    assert em["e_maxret_4"].iloc[t] > 0.19      # högsta 121,2


def test_metrics_need_minimum_sample() -> None:
    g = pd.DataFrame({"e_ret_5": [0.1] * 10, "e_maxret_5": [0.2] * 10, "e_maxdd_5": [-0.05] * 10})
    assert _metrics(g, 5) is None


def test_metrics_shape_and_values() -> None:
    n = 200
    g = pd.DataFrame({
        "e_ret_5": [0.05] * (n // 2) + [-0.05] * (n // 2),
        "e_maxret_5": [0.12] * n,
        "e_maxdd_5": [-0.11] * (n // 2) + [-0.02] * (n // 2),
    })
    m = _metrics(g, 5)
    assert m is not None
    assert m["win_rate"] == 0.5
    assert m["p_reach_10"] == 1.0
    assert m["p_dip_10"] == 0.5


def test_verdict_labels_follow_the_app_decision_tree() -> None:
    base = {"ret_1m": 0.0, "ret_3m": 0.0, "ret_12m": 0.0, "dist_52w_high": -0.20, "rvol_5_60": 1.0,
            "vol_accel": 0.0, "vol_expansion": 1.0, "breakout_20d": 0.0, "rvol_20_200": 1.0}
    rows = [
        {**base, "rvol_5_60": 3.5, "ret_1m": 0.30, "vol_expansion": 2.0},                         # utbrott
        {**base, "dist_52w_high": -0.03, "ret_3m": 0.10, "vol_accel": 0.2},                         # nära utbrott
        {**base, "vol_accel": 0.2, "ret_1m": 0.02, "dist_52w_high": -0.20},                         # uppbyggnad
        {**base, "ret_3m": -0.30, "ret_1m": -0.05, "dist_52w_high": -0.50},                         # fallande
        dict(base),                                                                                 # ingen signal
    ]
    labels = _verdict_labels(pd.DataFrame(rows)).tolist()
    assert labels == ["Utbrott pågår", "Nära utbrott", "Under uppbyggnad",
                      "Fallande — ingen vändning", "Ingen signal"]
