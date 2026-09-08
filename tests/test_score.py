"""Sanity checks for the preliminary composite score (marc.score.composite)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from marc.score import assess


def _peers(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "ret_3m": rng.normal(0, 0.15, n),
            "ret_6m": rng.normal(0, 0.20, n),
            "ret_12m": rng.normal(0, 0.30, n),
            "dist_52w_high": -np.abs(rng.normal(0.20, 0.12, n)),
            "rvol_5_60": np.abs(rng.normal(1.0, 0.4, n)) + 0.2,
            "vol_accel": rng.normal(0, 0.3, n),
        }
    )


def test_score_in_range_and_has_components() -> None:
    peers = _peers()
    b = assess(peers.iloc[10].to_dict(), peers, n_rules=1)
    assert 0.0 <= b.total <= 100.0
    assert {c.key for c in b.components} == {
        "momentum", "narhet_arshogsta", "volymintresse", "monster",
    }
    assert "ovaliderade" in b.note


def test_stronger_momentum_scores_higher() -> None:
    peers = _peers()
    weak = {"ret_3m": -0.4, "ret_6m": -0.4, "ret_12m": -0.5,
            "dist_52w_high": -0.5, "rvol_5_60": 0.6, "vol_accel": -0.3}
    strong = {"ret_3m": 0.5, "ret_6m": 0.6, "ret_12m": 0.9,
              "dist_52w_high": -0.01, "rvol_5_60": 2.5, "vol_accel": 1.0}
    assert assess(strong, peers, 3).total > assess(weak, peers, 0).total


def test_more_patterns_never_lowers_score() -> None:
    peers = _peers()
    row = peers.iloc[5].to_dict()
    assert assess(row, peers, 3).total >= assess(row, peers, 0).total
