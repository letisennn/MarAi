"""Uppbyggnadspoäng (marc.discovery.setup): motsatt inriktning mot Discovery
Score. Kärnkravet (Jonas, 2026-09-16): bolag redan nära årshögsta med stor
uppgång bakom sig ska ALDRIG ranka högt här — de ger inget informationsövertag."""

from __future__ import annotations

import numpy as np
import pandas as pd

from marc.discovery import assess_setup


def _peers(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    return pd.DataFrame(
        {
            "ret_1m": rng.normal(0, 0.08, n),
            "ret_3m": rng.normal(0, 0.15, n),
            "dist_52w_high": -np.abs(rng.normal(0.20, 0.12, n)),
            "rvol_5_60": np.abs(rng.normal(1.0, 0.4, n)) + 0.2,
            "vol_accel": rng.normal(0, 0.3, n),
            "search_accel": rng.normal(0, 0.4, n),
            "forum_accel": rng.normal(0, 0.4, n),
        }
    )


def test_setup_score_in_range_and_has_components() -> None:
    peers = _peers()
    b = assess_setup(peers.iloc[10].to_dict(), peers)
    assert 0.0 <= b.total <= 100.0
    assert {c.key for c in b.components} == {
        "volym_uppbyggnad", "uppmarksamhet", "lugn_kurs", "coiled_zon",
    }
    assert "ovaliderad" in b.note


def test_already_at_high_with_big_run_is_capped_and_flagged() -> None:
    """Kärnkravet: redan vid högsta + redan upp rejält -> lågt, flaggat. Vem som
    helst kan se det bolaget; scoren ska inte lyfta fram det."""
    peers = _peers()
    already_visible = {
        "ret_1m": 0.20, "ret_3m": 0.32, "dist_52w_high": -0.01,
        "rvol_5_60": 3.5, "vol_accel": 1.5, "search_accel": 0.5, "forum_accel": 0.5,
    }
    b = assess_setup(already_visible, peers)
    assert b.already_visible is True
    assert b.total <= 15.0


def test_quiet_price_rising_volume_below_high_scores_well() -> None:
    """Motsatsen: tyst kurs, stigande volym/uppmärksamhet, en bit under
    (inte vid) årshögsta -> ska ranka bra."""
    peers = _peers()
    setup_case = {
        "ret_1m": 0.01, "ret_3m": 0.02, "dist_52w_high": -0.20,
        "rvol_5_60": 2.2, "vol_accel": 0.8, "search_accel": 0.4, "forum_accel": 0.3,
    }
    already_run = {
        "ret_1m": 0.25, "ret_3m": 0.45, "dist_52w_high": -0.01,
        "rvol_5_60": 3.0, "vol_accel": 1.2, "search_accel": 0.6, "forum_accel": 0.4,
    }
    b_setup = assess_setup(setup_case, peers)
    b_run = assess_setup(already_run, peers)
    assert b_setup.total > b_run.total
    assert b_run.already_visible is True
    assert b_setup.already_visible is False


def test_coiled_zone_peaks_below_high_not_at_high() -> None:
    """Poängen för avstånd-till-högsta ska INTE vara monoton (närmare topp =
    inte alltid bättre) — den ska vara sämre precis vid toppen än en bit under."""
    peers = _peers()
    at_high = dict.fromkeys(("ret_1m", "ret_3m", "vol_accel", "search_accel", "forum_accel"), 0.0)
    at_high["dist_52w_high"] = -0.005
    at_high["rvol_5_60"] = 1.0
    under_high = dict(at_high)
    under_high["dist_52w_high"] = -0.20

    zone_at_high = next(c.score for c in assess_setup(at_high, peers).components if c.key == "coiled_zon")
    zone_under_high = next(c.score for c in assess_setup(under_high, peers).components if c.key == "coiled_zon")
    assert zone_under_high > zone_at_high


def test_calm_price_scores_higher_than_already_moved_price() -> None:
    peers = _peers()
    base = {"dist_52w_high": -0.20, "rvol_5_60": 1.0, "vol_accel": 0.0,
            "search_accel": 0.0, "forum_accel": 0.0}
    calm = {**base, "ret_1m": 0.005, "ret_3m": 0.01}
    moved = {**base, "ret_1m": 0.30, "ret_3m": 0.50}
    lugn_calm = next(c.score for c in assess_setup(calm, peers).components if c.key == "lugn_kurs")
    lugn_moved = next(c.score for c in assess_setup(moved, peers).components if c.key == "lugn_kurs")
    assert lugn_calm > lugn_moved
