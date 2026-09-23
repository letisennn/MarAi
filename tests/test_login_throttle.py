"""Inloggningen ska bromsa gissning av lösenord när appen ligger publikt."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import _gate  # noqa: E402


def _fresh() -> None:
    _gate._failed_attempts().clear()


def test_not_locked_before_max_fails() -> None:
    _fresh()
    for i in range(_gate.MAX_FAILS - 1):
        _gate._register_failure("hugo", now=1000.0 + i)
    assert _gate._locked_for("hugo", now=1010.0) == 0


def test_locks_after_max_fails_then_expires() -> None:
    _fresh()
    for i in range(_gate.MAX_FAILS):
        _gate._register_failure("hugo", now=1000.0 + i)
    left = _gate._locked_for("hugo", now=1010.0)
    assert 0 < left <= _gate.LOCK
    assert _gate._locked_for("hugo", now=1000.0 + _gate.WINDOW + _gate.LOCK + 60) == 0


def test_lock_is_per_user() -> None:
    _fresh()
    for i in range(_gate.MAX_FAILS):
        _gate._register_failure("hugo", now=1000.0 + i)
    assert _gate._locked_for("jonas", now=1010.0) == 0
