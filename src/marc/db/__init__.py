"""Database access — DuckDB.

`data/marc.duckdb` is the database. The pipeline opens it read-write (single
writer); the Streamlit app opens it read-only. Raw source dumps are also written
as immutable Parquet under `data/raw/` for provenance.
"""

from marc.db.migrate import run_migrations
from marc.db.session import connect, read_only_connect

__all__ = ["connect", "read_only_connect", "run_migrations"]
