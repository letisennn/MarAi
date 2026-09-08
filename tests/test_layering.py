"""Guardrail: ``marc.features`` must never import ``marc.targets`` (the leakage
boundary — targets use future data by design).

Parses real import statements with ``ast`` so docstring mentions don't count.
"""

from __future__ import annotations

import ast
import pathlib

FEATURES_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "marc" / "features"


def _imports(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def test_features_does_not_import_targets() -> None:
    offenders = [
        str(p) for p in FEATURES_DIR.rglob("*.py")
        if any(m == "marc.targets" or m.startswith("marc.targets.") for m in _imports(p))
    ]
    assert not offenders, f"features must not import targets: {offenders}"
