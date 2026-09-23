"""Förregistrerade regel-masker (src/marc/signals/rules.py). rule4 tillagd
2026-09-19: samma villkor som verdict()s "Under uppbyggnad" i app/_data.py —
ska vara förregistrerad och backtestbar, inte bara en oregistrerad heuristik."""

from __future__ import annotations

import pandas as pd

from marc.signals.rules import _rule_masks


def _row(**kw) -> pd.DataFrame:
    base = {
        "rvol_5_60": 1.0, "ret_1m": 0.0, "vol_expansion": 1.0, "breakout_20d": 0,
        "rvol_20_200": 1.0, "dist_52w_high": -0.20, "ret_3m": 0.0, "vol_accel": 0.0,
    }
    base.update(kw)
    return pd.DataFrame([base])


def test_rule4_fires_on_quiet_price_rising_volume_below_high() -> None:
    w = _row(vol_accel=0.1, ret_1m=0.05, dist_52w_high=-0.20)
    masks = _rule_masks(w)
    assert bool(masks["rule4"].iloc[0]) is True


def test_rule4_does_not_fire_when_already_near_high() -> None:
    # samma volym/prisläge, men nära årshögsta -> hör hemma i rule3/"redan synligt", inte rule4
    w = _row(vol_accel=0.1, ret_1m=0.05, dist_52w_high=-0.02)
    masks = _rule_masks(w)
    assert bool(masks["rule4"].iloc[0]) is False


def test_rule4_does_not_fire_when_price_already_moved_a_lot() -> None:
    w = _row(vol_accel=0.1, ret_1m=0.25, dist_52w_high=-0.20)
    masks = _rule_masks(w)
    assert bool(masks["rule4"].iloc[0]) is False


def test_rule4_does_not_fire_without_volume_buildup() -> None:
    w = _row(vol_accel=-0.1, rvol_5_60=1.0, ret_1m=0.05, dist_52w_high=-0.20)
    masks = _rule_masks(w)
    assert bool(masks["rule4"].iloc[0]) is False


def test_all_four_rules_present() -> None:
    w = _row()
    masks = _rule_masks(w)
    assert set(masks) == {"rule1", "rule2", "rule3", "rule4"}
