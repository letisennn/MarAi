"""FX to base currency (SEK).

v0.1 uses **constant** cross rates for every trading date — a deliberate
simplification. A real point-in-time source (Riksbank / ECB SDW) drops in here
later without touching downstream code, which only reads ``fx_rate_daily``.
"""

from __future__ import annotations

import duckdb

from marc.config import get_logger

log = get_logger(__name__)

# 1 unit of quote_ccy = RATE SEK  (rough long-run levels; illustrative)
_RATES = {"SEK": 1.0, "NOK": 0.98, "DKK": 1.52, "EUR": 11.35, "USD": 10.60}


def build_fx_rates(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("DELETE FROM fx_rate_daily WHERE source = 'const_v0'")
    values = ", ".join(f"('{c}', {r})" for c, r in _RATES.items())
    con.execute(
        f"""
        INSERT INTO fx_rate_daily (base_ccy, quote_ccy, session_date, rate, source)
        SELECT 'SEK', v.ccy, d.session_date, v.rate, 'const_v0'
        FROM (SELECT DISTINCT session_date FROM price_daily) d
        CROSS JOIN (VALUES {values}) AS v(ccy, rate)
        """
    )
    n = con.execute("SELECT count(*) FROM fx_rate_daily").fetchone()[0]
    log.info("fx: wrote %d constant-rate rows", n)
    return int(n)
