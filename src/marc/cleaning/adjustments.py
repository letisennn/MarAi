"""As-of split/dividend back-adjustment factors.

Prices stay unadjusted in ``price_daily``. Here we derive, per (security, date),
cumulative factors such that ``adjusted = close * cum_split_factor *
cum_div_factor`` gives a series comparable across corporate actions, where the
factors only fold in actions with ``ex_date`` strictly after the date (standard
back-adjustment). Rows are written only for securities that have actions;
everything else COALESCEs to 1.0 in ``price_clean``.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from marc.config import get_logger

log = get_logger(__name__)


def build_adjustment_factors(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("DELETE FROM adjustment_factor WHERE method = 'seed_v0'")

    acts = con.execute(
        """
        SELECT security_id, action_type, ex_date, ratio, cash_amount
        FROM corporate_action
        WHERE action_type IN ('split', 'dividend') AND ex_date IS NOT NULL
        """
    ).df()
    if acts.empty:
        log.info("adjustments: no split/dividend actions")
        return 0

    total = 0
    for sid, grp in acts.groupby("security_id"):
        px = con.execute(
            "SELECT session_date, close FROM price_daily WHERE security_id = ? ORDER BY session_date",
            [int(sid)],
        ).df()
        if px.empty:
            continue
        px["session_date"] = pd.to_datetime(px["session_date"])
        px = px.set_index("session_date")
        csf = pd.Series(1.0, index=px.index)
        cdf = pd.Series(1.0, index=px.index)

        for _, a in grp.iterrows():
            ex = pd.Timestamp(a["ex_date"])
            before = px.index < ex  # actions after a date adjust that date
            if a["action_type"] == "split" and pd.notna(a["ratio"]) and a["ratio"]:
                csf.loc[before] *= 1.0 / float(a["ratio"])
            elif a["action_type"] == "dividend" and pd.notna(a["cash_amount"]):
                prev = px["close"].reindex(px.index[px.index < ex])
                c_prev = prev.iloc[-1] if len(prev) else np.nan
                if pd.notna(c_prev) and c_prev > 0:
                    cdf.loc[before] *= max(1.0 - float(a["cash_amount"]) / float(c_prev), 0.01)

        out = pd.DataFrame(
            {
                "security_id": int(sid),
                "session_date": px.index.date,
                "cum_split_factor": csf.to_numpy(),
                "cum_div_factor": cdf.to_numpy(),
                "method": "seed_v0",
            }
        )
        con.register("adj_df", out)
        con.execute(
            """
            INSERT OR REPLACE INTO adjustment_factor
                (security_id, session_date, cum_split_factor, cum_div_factor, computed_at, method)
            SELECT security_id, session_date, cum_split_factor, cum_div_factor, now(), method
            FROM adj_df
            """
        )
        con.unregister("adj_df")
        total += len(out)

    log.info("adjustments: wrote %d factor rows for %d securities",
             total, acts["security_id"].nunique())
    return total
