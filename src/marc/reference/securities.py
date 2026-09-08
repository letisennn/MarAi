"""Load the illustrative seed universe into the reference tables.

Populates ``security`` (+ ``status_date`` / ``status_detail``), ``security_xref``
(ticker + MIC with validity ranges), ``shares_outstanding`` (one constant row per
name for v0.1) and ``listing_status_history``.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from marc.config import get_logger, project_path

log = get_logger(__name__)

SEED_DIR = project_path("data", "seed")


def load_seed_securities(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    secs = pd.read_csv(SEED_DIR / "securities.csv")
    con.register("seed_secs", secs)

    con.execute(
        """
        INSERT INTO security
            (isin, name, country, currency, base_listing_mic, sector, share_class,
             first_listed_date, status, status_date, status_detail)
        SELECT isin, name, country, currency, mic, sector, 'common',
               CAST(list_date AS DATE), status,
               CAST(status_date AS DATE), CAST(status_detail AS TEXT)
        FROM seed_secs
        WHERE isin NOT IN (SELECT isin FROM security)
        """
    )
    con.execute(
        """
        UPDATE security SET status = s.status,
                            status_date = CAST(s.status_date AS DATE),
                            status_detail = CAST(s.status_detail AS TEXT)
        FROM seed_secs s WHERE security.isin = s.isin
        """
    )

    ids = con.execute("SELECT security_id, isin FROM security").df()
    j = secs.merge(ids, on="isin", how="left")
    con.register("seed_j", j)

    con.execute("DELETE FROM security_xref WHERE source = 'seed'")
    con.execute(
        """
        INSERT INTO security_xref (security_id, id_type, id_value, valid_from, valid_to, source)
        SELECT security_id, 'ticker', yahoo, CAST(list_date AS DATE), CAST(status_date AS DATE), 'seed'
        FROM seed_j WHERE yahoo IS NOT NULL
        UNION ALL
        SELECT security_id, 'mic', mic, CAST(list_date AS DATE), CAST(status_date AS DATE), 'seed'
        FROM seed_j WHERE mic IS NOT NULL
        """
    )

    con.execute("DELETE FROM shares_outstanding WHERE source = 'seed'")
    con.execute(
        """
        INSERT INTO shares_outstanding (security_id, as_of_date, knowledge_time, shares, source)
        SELECT security_id, CAST(list_date AS DATE), CAST(list_date AS TIMESTAMP),
               shares_out_millions * 1e6, 'seed'
        FROM seed_j
        """
    )

    con.execute("DELETE FROM listing_status_history WHERE source = 'seed'")
    con.execute(
        """
        INSERT INTO listing_status_history
            (security_id, status, market_segment, valid_from, valid_to, reason, source)
        SELECT security_id, 'listed', market_segment, CAST(list_date AS DATE),
               CAST(status_date AS DATE), NULL, 'seed'
        FROM seed_j
        """
    )
    con.execute(
        """
        INSERT INTO listing_status_history
            (security_id, status, market_segment, valid_from, valid_to, reason, source)
        SELECT security_id, status, market_segment, CAST(status_date AS DATE), NULL,
               CAST(status_detail AS TEXT), 'seed'
        FROM seed_j
        WHERE status IN ('delisted','acquired','bankrupt') AND status_date IS NOT NULL
        """
    )

    for name in ("seed_secs", "seed_j"):
        con.unregister(name)
    log.info("seed: loaded %d securities (%d dead)", len(secs),
             int((secs["status"] != "listed").sum()))
    return secs
