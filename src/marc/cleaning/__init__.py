"""Data cleaning — validated, currency-normalised, adjustment-aware views.

``price_clean`` is the single view the feature/target/universe layers read. It is
a view (cheap to rebuild), not a stored table.
"""

from __future__ import annotations

import duckdb

from marc.cleaning.adjustments import build_adjustment_factors
from marc.cleaning.fx import build_fx_rates
from marc.cleaning.validate import validate_prices
from marc.config import get_logger

log = get_logger(__name__)

_PRICE_CLEAN_VIEW = """
CREATE OR REPLACE VIEW price_clean AS
WITH sh AS (
    SELECT security_id, any_value(shares) AS shares
    FROM shares_outstanding GROUP BY security_id
),
fx AS (
    SELECT quote_ccy, session_date, rate FROM fx_rate_daily WHERE base_ccy = 'SEK'
)
SELECT
    p.security_id,
    p.session_date,
    s.country,
    s.currency,
    p.open  AS open_local,
    p.high  AS high_local,
    p.low   AS low_local,
    p.close AS close_local,
    p.volume,
    COALESCE(fx.rate, 1.0)              AS fx_rate,
    COALESCE(af.cum_split_factor, 1.0)  AS csf,
    COALESCE(af.cum_div_factor, 1.0)    AS cdf,
    p.close * COALESCE(fx.rate, 1.0)    AS close_sek,
    p.close * COALESCE(fx.rate, 1.0) * COALESCE(af.cum_split_factor, 1.0) * COALESCE(af.cum_div_factor, 1.0) AS adj_close_sek,
    p.high  * COALESCE(fx.rate, 1.0) * COALESCE(af.cum_split_factor, 1.0) * COALESCE(af.cum_div_factor, 1.0) AS adj_high_sek,
    p.low   * COALESCE(fx.rate, 1.0) * COALESCE(af.cum_split_factor, 1.0) * COALESCE(af.cum_div_factor, 1.0) AS adj_low_sek,
    p.volume * p.close * COALESCE(fx.rate, 1.0) AS turnover_sek,
    p.close * COALESCE(fx.rate, 1.0) * COALESCE(af.cum_split_factor, 1.0) * COALESCE(sh.shares, 0) AS market_cap_sek
FROM price_daily p
JOIN security s USING (security_id)
LEFT JOIN fx ON fx.quote_ccy = s.currency AND fx.session_date = p.session_date
LEFT JOIN adjustment_factor af ON af.security_id = p.security_id AND af.session_date = p.session_date
LEFT JOIN sh ON sh.security_id = p.security_id
"""


def build_price_clean_view(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(_PRICE_CLEAN_VIEW)
    log.info("cleaning: price_clean view (re)built")


def run_cleaning(con: duckdb.DuckDBPyConnection) -> dict:
    flags = validate_prices(con)
    build_fx_rates(con)
    n_adj = build_adjustment_factors(con)
    build_price_clean_view(con)
    return {"flags": flags, "adjustment_rows": n_adj}


__all__ = [
    "run_cleaning",
    "build_price_clean_view",
    "build_fx_rates",
    "build_adjustment_factors",
    "validate_prices",
]
