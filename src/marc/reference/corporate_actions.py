"""Load corporate actions.

Splits and dividends come from ``data/seed/corporate_actions.csv``. Delisting /
acquisition / bankruptcy actions are derived from ``security.status`` /
``status_date`` / ``status_detail`` so the seed CSV holds only price-adjusting
events.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from marc.config import get_logger, project_path

log = get_logger(__name__)
SEED_DIR = project_path("data", "seed")


def load_corporate_actions(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("DELETE FROM corporate_action WHERE source IN ('seed', 'derived')")

    ca = pd.read_csv(SEED_DIR / "corporate_actions.csv")
    ids = con.execute("SELECT security_id, isin FROM security").df()
    ca = ca.merge(ids, on="isin", how="left").dropna(subset=["security_id"])
    ca["security_id"] = ca["security_id"].astype("int64")
    con.register("ca_df", ca)
    con.execute(
        """
        INSERT INTO corporate_action
            (security_id, action_type, announce_date, ex_date, record_date, pay_date,
             ratio, cash_amount, currency, details, source, ingested_at)
        SELECT security_id, action_type, NULL, CAST(ex_date AS DATE), NULL, NULL,
               ratio, cash_amount, currency, to_json(detail), 'seed', now()
        FROM ca_df
        """
    )
    con.unregister("ca_df")

    # derived delisting / acquisition / bankruptcy events
    con.execute(
        """
        INSERT INTO corporate_action
            (security_id, action_type, announce_date, ex_date, record_date, pay_date,
             ratio, cash_amount, currency, details, source, ingested_at)
        SELECT security_id,
               CASE status WHEN 'acquired' THEN 'acquisition'
                           WHEN 'bankrupt' THEN 'bankruptcy'
                           ELSE 'delisting' END,
               NULL, status_date, NULL, NULL, NULL,
               TRY_CAST(status_detail AS DOUBLE), currency, to_json(status_detail), 'derived', now()
        FROM security
        WHERE status IN ('delisted','acquired','bankrupt') AND status_date IS NOT NULL
        """
    )

    n = con.execute("SELECT count(*) FROM corporate_action").fetchone()[0]
    log.info("corporate actions: %d rows (incl. derived delistings)", n)
    return int(n)
