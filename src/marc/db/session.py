"""DuckDB connection helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from marc.config import get_settings


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open the project database. Pipeline code uses ``read_only=False``."""
    settings = get_settings()
    path = settings.abs_db_path
    if not read_only:
        _ensure_parent(path)
    return duckdb.connect(str(path), read_only=read_only)


def read_only_connect() -> duckdb.DuckDBPyConnection:
    return connect(read_only=True)


@contextmanager
def session(read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
    con = connect(read_only=read_only)
    try:
        yield con
    finally:
        con.close()
