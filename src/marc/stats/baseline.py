"""E1a — unconditional large-move base rates (the control group).

Headline numbers use ``cap_segment_at_entry = 'small'`` observations; ``mid`` is
reported alongside for context only.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from marc.config import get_logger, targets_config
from marc.stats._panel import wilson_ci
from marc.stats._results import write_result

log = get_logger(__name__)


def _event_names() -> list[str]:
    return [e["name"] for e in targets_config()["events"]]


def _rate(con, eid, events, df, subset_base: dict, oos: bool) -> None:
    for ev in events:
        s = df[ev].dropna()
        n, k = len(s), int(s.sum())
        if n == 0:
            continue
        lo, hi = wilson_ci(k, n)
        write_result(con, eid, f"base_rate:{ev}", k / n,
                     subset={**subset_base, "event": ev},
                     ci_low=lo, ci_high=hi, n_obs=n, n_events=k, is_out_of_sample=oos)


def base_rates(con: duckdb.DuckDBPyConnection, experiment_id: int, wide: pd.DataFrame) -> dict:
    events = _event_names()
    small = wide[wide["cap_segment_at_entry"] == "small"]
    mid = wide[wide["cap_segment_at_entry"] == "mid"]

    _rate(con, experiment_id, events, small, {"segment": "small", "slice": "pooled"}, oos=False)
    _rate(con, experiment_id, events, mid, {"segment": "mid", "slice": "pooled"}, oos=False)

    for yr, g in small.groupby("year"):
        _rate(con, experiment_id, events, g, {"segment": "small", "slice": "year", "year": int(yr)}, oos=False)
    for country, g in small.groupby("country"):
        _rate(con, experiment_id, events, g, {"segment": "small", "slice": "country", "country": country}, oos=False)

    summary = {}
    for ev in events:
        s = small[ev].dropna()
        if len(s):
            summary[ev] = round(float(s.mean()), 4)
    log.info("E1a base rates (small, pooled): %s", summary)
    return summary
