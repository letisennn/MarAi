"""Time-varying universe membership.

Membership is evaluated at each month-end (point-in-time market cap, 60-day
median turnover, price floor, minimum history) and stored as valid_from/valid_to
intervals in ``universe_membership``. Admission requires market cap ≤ the small
cap ceiling; a name admitted as "small" that grows past it is retained (its
observations are later tagged ``cap_segment_at_entry = 'mid'``). The per-
observation cap segment and market cap are taken directly from ``price_clean``
at the observation date by the panel builder — this module only decides the
in/out boolean.
"""

from __future__ import annotations

import json

import duckdb
import pandas as pd

from marc.config import get_logger, universe_config

log = get_logger(__name__)


def cap_segment(market_cap_sek: float, small_max: float) -> str:
    return "small" if market_cap_sek <= small_max else "mid"


def _month_end_trading_days(trading_days: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    td = trading_days[(trading_days >= start) & (trading_days <= end)]
    if td.empty:
        return []
    by_month = td.groupby(td.dt.to_period("M")).max()
    return list(by_month.sort_values())


def build_universe(con: duckdb.DuckDBPyConnection) -> int:
    cfg = universe_config()
    name = cfg["universe_name"]
    mc_min = float(cfg["market_cap_sek"]["min"])
    mc_max = float(cfg["market_cap_sek"]["max"])
    small_max = float(cfg["cap_segments"]["small_max_market_cap_sek"])
    retain = bool(cfg["cap_segments"].get("retain_after_growth", True))
    liq_floor = float(cfg["liquidity_floor_sek_median_turnover_60d"])
    price_floor = float(cfg["price_floor_local"])
    min_hist = int(cfg["min_history_trading_days"])
    start = pd.Timestamp(cfg["study_start"])
    end = pd.Timestamp(cfg["study_end"])

    px = con.execute(
        "SELECT security_id, session_date, close_local, market_cap_sek, turnover_sek "
        "FROM price_clean ORDER BY security_id, session_date"
    ).df()
    if px.empty:
        log.warning("universe: price_clean is empty")
        return 0
    px["session_date"] = pd.to_datetime(px["session_date"])
    px["med_turn_60"] = (
        px.groupby("security_id")["turnover_sek"]
        .rolling(60, min_periods=20).median().reset_index(level=0, drop=True)
    )
    px["n_hist"] = px.groupby("security_id").cumcount() + 1

    month_ends = _month_end_trading_days(px["session_date"].drop_duplicates().sort_values(), start, end)
    me_df = pd.DataFrame({"session_date": month_ends})

    monthly = []
    for sid, g in px.groupby("security_id"):
        g = g.sort_values("session_date")
        snap = pd.merge_asof(
            me_df, g, on="session_date", direction="backward",
            tolerance=pd.Timedelta(days=7),
        )
        snap["security_id"] = sid
        monthly.append(snap)
    monthly = pd.concat(monthly, ignore_index=True).dropna(subset=["close_local"])

    # evaluate month-by-month with retention
    monthly = monthly.sort_values(["session_date", "security_id"])
    member_prev: set[int] = set()
    rows = []
    for me, chunk in monthly.groupby("session_date"):
        member_now: set[int] = set()
        for _, r in chunk.iterrows():
            sid = int(r["security_id"])
            mc = float(r["market_cap_sek"])
            eligible_liq = pd.notna(r["med_turn_60"]) and r["med_turn_60"] >= liq_floor
            eligible_price = r["close_local"] >= price_floor
            eligible_hist = r["n_hist"] >= min_hist
            size_ok = mc >= mc_min and (
                mc <= mc_max or (retain and sid in member_prev)
            )
            in_u = bool(size_ok and eligible_liq and eligible_price and eligible_hist)
            seg = cap_segment(mc, small_max)
            rows.append(
                {
                    "security_id": sid,
                    "month_end": me,
                    "in_universe": in_u,
                    "market_cap_sek": mc,
                    "cap_segment": seg,
                    "med_turn_60": float(r["med_turn_60"]) if pd.notna(r["med_turn_60"]) else None,
                }
            )
            if in_u:
                member_now.add(sid)
        member_prev = member_now

    mdf = pd.DataFrame(rows)

    # compress consecutive in_universe month-ends into intervals
    con.execute("DELETE FROM universe_membership WHERE universe_name = ?", [name])
    n_intervals = 0
    ordered_me = sorted(mdf["month_end"].unique())
    for sid, g in mdf.sort_values("month_end").groupby("security_id"):
        g = g.set_index("month_end")
        run_start = None
        entry_mc = 0.0
        entry_seg = "small"
        for me in ordered_me:
            row = g.loc[me] if me in g.index else None
            active = row is not None and bool(row["in_universe"])
            if active and run_start is None:
                run_start = me
                entry_mc = float(row["market_cap_sek"])
                entry_seg = str(row["cap_segment"])
            if (not active) and run_start is not None:
                _insert_interval(con, name, int(sid), run_start, me, entry_mc, entry_seg,
                                 mc_min, mc_max, liq_floor)
                n_intervals += 1
                run_start = None
        if run_start is not None:
            _insert_interval(con, name, int(sid), run_start, None, entry_mc, entry_seg,
                             mc_min, mc_max, liq_floor)
            n_intervals += 1

    log.info("universe: %d membership intervals over %d month-ends", n_intervals, len(ordered_me))
    return n_intervals


def _insert_interval(con, name, sid, valid_from, valid_to, entry_mc, entry_seg,
                     mc_min, mc_max, liq_floor) -> None:
    snap = json.dumps(
        {
            "entry_market_cap_sek": round(entry_mc, 2),
            "entry_cap_segment": entry_seg,
            "thresholds": {"mc_min": mc_min, "mc_max": mc_max, "liq_floor_60d_median": liq_floor},
        }
    )
    con.execute(
        """
        INSERT INTO universe_membership
            (universe_name, security_id, valid_from, valid_to, entry_reason, exit_reason, criteria_snapshot)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [name, sid,
         pd.Timestamp(valid_from).date(),
         pd.Timestamp(valid_to).date() if valid_to is not None else None,
         "meets_criteria", None if valid_to is None else "fails_criteria", snap],
    )


def members_asof(con: duckdb.DuckDBPyConnection, universe_name: str, on_date) -> set[int]:
    rows = con.execute(
        """
        SELECT DISTINCT security_id FROM universe_membership
        WHERE universe_name = ? AND valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)
        """,
        [universe_name, on_date, on_date],
    ).fetchall()
    return {r[0] for r in rows}
