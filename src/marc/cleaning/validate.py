"""Sanity checks on raw prices. Flags and logs; never deletes."""

from __future__ import annotations

import duckdb

from marc.config import get_logger

log = get_logger(__name__)

_CHECKS = {
    "high_lt_low": "high < low",
    "close_out_of_range": "close < low OR close > high",
    "neg_or_zero_close": "close <= 0",
    "neg_volume": "volume < 0",
    "extreme_1d_move": (
        "abs(close / lag(close) OVER (PARTITION BY security_id ORDER BY session_date) - 1) > 0.9"
    ),
}


def validate_prices(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, pred in _CHECKS.items():
        n = con.execute(
            f"SELECT count(*) FROM (SELECT *, {pred} AS _flag FROM price_daily) WHERE _flag"
        ).fetchone()[0]
        counts[name] = int(n)
    total_rows = con.execute("SELECT count(*) FROM price_daily").fetchone()[0]
    log.info("validate: %d price rows; flags=%s", total_rows, counts)
    return counts
