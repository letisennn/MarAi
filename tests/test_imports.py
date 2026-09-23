"""Varje modul ska gå att importera FÖRST i en ny process — cirkulära importer
döljs annars av att en annan modul råkar importeras tidigare (2026-09-24:
playbook drog in marc.signals och `marc refresh`/`marc signals` föll på
'partially initialized module')."""

from __future__ import annotations

import subprocess
import sys

import pytest

MODULES = [
    "marc.signals", "marc.stats", "marc.stats.playbook", "marc.pipeline",
    "marc.discovery", "marc.panel", "marc.cli", "marc.paper",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports_first_in_a_fresh_process(module: str) -> None:
    res = subprocess.run([sys.executable, "-c", f"import {module}"], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr[-600:]
