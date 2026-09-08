"""Helper for writing experiment_result rows."""

from __future__ import annotations

import json

import duckdb


def write_result(
    con: duckdb.DuckDBPyConnection,
    experiment_id: int,
    metric_name: str,
    value: float | None,
    *,
    subset: dict | None = None,
    ci_low: float | None = None,
    ci_high: float | None = None,
    n_obs: int | None = None,
    n_events: int | None = None,
    is_out_of_sample: bool = False,
    passed: bool | None = None,
    params: dict | None = None,
) -> None:
    con.execute(
        """
        INSERT INTO experiment_result
            (experiment_id, metric_name, subset, value, ci_low, ci_high, n_obs, n_events,
             is_out_of_sample, passed, params)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            experiment_id, metric_name,
            json.dumps(subset) if subset else None,
            _f(value), _f(ci_low), _f(ci_high),
            int(n_obs) if n_obs is not None else None,
            int(n_events) if n_events is not None else None,
            is_out_of_sample, passed,
            json.dumps(params) if params else None,
        ],
    )


def _f(x) -> float | None:
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    return None if xf != xf else xf  # drop NaN
