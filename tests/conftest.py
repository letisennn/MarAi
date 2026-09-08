"""Shared fixtures.

``pipeline_db`` runs the full synthetic v0.1 pipeline once into a temp database
and hands back a read-only connection. It is session-scoped (~20-30s once).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(scope="session")
def pipeline_db(tmp_path_factory: pytest.TempPathFactory) -> duckdb.DuckDBPyConnection:
    db = tmp_path_factory.mktemp("marcdb") / "marc.duckdb"
    os.environ["MARC_DB_PATH"] = str(db)

    from marc import config

    config.get_settings.cache_clear()
    from marc.pipeline import run_all

    run_all(source="synthetic", reset=True)
    con = duckdb.connect(str(db), read_only=True)
    yield con
    con.close()
