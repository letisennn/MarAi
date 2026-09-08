"""Numbered ``.sql`` migration runner.

Applies ``migrations/NNNN_*.sql`` in order, tracked in ``schema_migrations``.
Statements are split on ``;`` — our migration files keep no semicolons inside
string literals, so a naive split is safe.
"""

from __future__ import annotations

import hashlib
import re

import duckdb

from marc.config import get_logger, project_path

log = get_logger(__name__)

_MIGRATIONS_DIR = project_path("migrations")
_FILENAME_RE = re.compile(r"^(\d+)_.*\.sql$")


def _split_statements(sql: str) -> list[str]:
    # strip full-line and trailing ``--`` comments first (our migrations keep no
    # ``--`` inside string literals), then split on ``;``.
    stripped = []
    for line in sql.splitlines():
        i = line.find("--")
        stripped.append(line if i == -1 else line[:i])
    body = "\n".join(stripped)
    return [s.strip() for s in body.split(";") if s.strip()]


def _discover() -> list[tuple[int, object]]:
    found = []
    for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        m = _FILENAME_RE.match(path.name)
        if m:
            found.append((int(m.group(1)), path))
    return found


def run_migrations(con: duckdb.DuckDBPyConnection) -> list[int]:
    con.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT now(), checksum TEXT)"
    )
    applied_rows = con.execute("SELECT version FROM schema_migrations").fetchall()
    applied = {r[0] for r in applied_rows}

    newly = []
    for version, path in _discover():
        if version in applied:
            continue
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode()).hexdigest()[:16]
        log.info("applying migration %04d (%s)", version, path.name)
        con.execute("BEGIN")
        try:
            for stmt in _split_statements(sql):
                con.execute(stmt)
            con.execute(
                "INSERT INTO schema_migrations (version, checksum) VALUES (?, ?)",
                [version, checksum],
            )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        newly.append(version)

    if not newly:
        log.info("database schema up to date")
    return newly
