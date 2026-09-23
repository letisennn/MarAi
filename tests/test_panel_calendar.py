"""En enda avvikande ticker fick tidigare kapa hela veckans panel-observation
för ALLA bolag (2026-09-19: ShaMaran Petroleum ensam på en dag höll tillbaka
hela panelen en vecka). ``_trading_calendar`` ska ignorera sådana dagar."""

from __future__ import annotations

import duckdb
import pandas as pd

from marc.panel import _trading_calendar


def _con_with_price_clean(rows: list[tuple[int, str]]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE price_clean (security_id INTEGER, session_date DATE)")
    if rows:
        con.executemany("INSERT INTO price_clean VALUES (?, ?)", rows)
    return con


def test_outlier_ticker_alone_on_a_date_is_excluded() -> None:
    # 10 bolag handlar båda "riktiga" dagarna; ett enda bolag har dessutom en
    # rad en dag senare som ingen annan har.
    rows = [(sid, "2026-09-16") for sid in range(1, 11)]
    rows += [(sid, "2026-09-11") for sid in range(1, 11)]
    rows += [(1, "2026-09-18")]  # avvikaren, ensam
    con = _con_with_price_clean(rows)

    cal = _trading_calendar(con)

    assert pd.Timestamp("2026-09-16") in cal
    assert pd.Timestamp("2026-09-11") in cal
    assert pd.Timestamp("2026-09-18") not in cal


def test_broadly_covered_date_is_kept() -> None:
    rows = [(sid, "2026-09-16") for sid in range(1, 11)]
    rows += [(sid, "2026-09-18") for sid in range(1, 9)]  # 8/10 = 80 %, brett täckt
    con = _con_with_price_clean(rows)

    cal = _trading_calendar(con)

    assert pd.Timestamp("2026-09-18") in cal


def test_empty_price_clean_returns_empty_calendar() -> None:
    con = _con_with_price_clean([])
    cal = _trading_calendar(con)
    assert len(cal) == 0
