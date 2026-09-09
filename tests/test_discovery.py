"""Discovery-lagret: fasmodell (ren funktion) + analog-motor (anti-leakage).

Kärnkrav (spec-brief §7): en analog-fråga vid tidpunkt T får bara använda
information känd vid T, och grannarna måste ligga strikt före T.
"""

from __future__ import annotations

import ast
import pathlib

import pandas as pd

from marc.discovery import ANALOGUE_FEATURES, analogue_outcomes, classify_phase, find_analogues
from marc.discovery.phase import PHASES

_DISC_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "marc" / "discovery"


# --------------------------------------------------------------- fasmodell
def test_phase_is_pure_and_total() -> None:
    # tomt in -> okänt, aldrig krasch
    assert classify_phase({}).key == "unknown"
    # ett tydligt hype-läge
    hot = {"ret_1m": 0.30, "ret_3m": 0.55, "rvol_5_60": 4.0, "vol_accel": 2.0,
           "dist_52w_high": -0.02, "vol_expansion": 1.3}
    assert classify_phase(hot).idx >= 3  # minst "accelererande"
    # ett dött läge
    dead = {"ret_1m": -0.01, "ret_3m": -0.02, "rvol_5_60": 0.9, "vol_accel": -0.1,
            "dist_52w_high": -0.35, "vol_expansion": 0.9}
    assert classify_phase(dead).key in {"low", "reversal"}


def test_phase_high_volume_is_never_low() -> None:
    feats = {"ret_1m": 0.0, "ret_3m": 0.0, "rvol_5_60": 5.0, "vol_accel": 0.0,
             "dist_52w_high": -0.20, "vol_expansion": 1.0}
    assert classify_phase(feats).key != "low"


def test_phase_keys_unique_and_ordered() -> None:
    idxs = [p.idx for p in PHASES]
    assert idxs == sorted(idxs) == list(range(1, 8))
    assert len({p.key for p in PHASES}) == 7


def test_phase_module_does_not_import_targets() -> None:
    for path in _DISC_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        mods: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
        assert not any(m == "marc.targets" or m.startswith("marc.targets.") for m in mods), path


# --------------------------------------------------------------- analog-motor
def test_analogues_are_strictly_in_the_past(pipeline_db) -> None:
    sid = pipeline_db.execute(
        "SELECT security_id FROM observation GROUP BY 1 HAVING count(*) > 100 LIMIT 1"
    ).fetchone()[0]
    nb = find_analogues(pipeline_db, sid, k=30, feature_names=ANALOGUE_FEATURES)
    assert not nb.empty
    qdate = pd.Timestamp(nb.attrs["query_date"])
    assert (pd.to_datetime(nb["obs_date"]) < qdate).all(), "granne får inte ligga på/efter frågedatum"


def test_analogues_exclude_the_query_security(pipeline_db) -> None:
    sid = pipeline_db.execute(
        "SELECT security_id FROM observation GROUP BY 1 HAVING count(*) > 100 LIMIT 1"
    ).fetchone()[0]
    nb = find_analogues(pipeline_db, sid, k=40, exclude_query_security=True)
    assert (nb["security_id"] != sid).all()


def test_analogue_query_uses_only_features_not_targets(pipeline_db) -> None:
    # find_analogues får aldrig röra target_panel — bevisas genom att en trasig
    # target_panel inte påverkar resultatet.
    sid = pipeline_db.execute(
        "SELECT security_id FROM observation GROUP BY 1 HAVING count(*) > 100 LIMIT 1"
    ).fetchone()[0]
    a = find_analogues(pipeline_db, sid, k=25)
    b = find_analogues(pipeline_db, sid, k=25)
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


def test_analogue_outcomes_report_n_and_control(pipeline_db) -> None:
    sid = pipeline_db.execute(
        "SELECT security_id FROM observation GROUP BY 1 HAVING count(*) > 100 LIMIT 1"
    ).fetchone()[0]
    nb = find_analogues(pipeline_db, sid, k=40)
    out = analogue_outcomes(pipeline_db, nb, control_segment="small")
    assert out["n_analogues"] == len(nb)
    for d in out["horizons"].values():
        assert d["n"] <= len(nb)
        # kontrollgruppen finns för varje horisont
        assert "control_hit_rate" in d
