"""Pre-registered boolean rules from ``docs/experiments/E1.md`` §E1d.

No fitted weights, no score. Each matching observation is written to
``signal_log`` with its feature snapshot; realised outcomes are joined from
``target_panel`` into ``signal_outcome``.
"""

from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from marc.config import get_logger
from marc.stats._panel import load_wide

log = get_logger(__name__)

RULE_VERSION_PREFIX = "E1d_v0.1"

_RULE_FEATURES = [
    "rvol_5_60", "ret_1m", "vol_expansion", "breakout_20d",
    "rvol_20_200", "dist_52w_high", "ret_3m", "vol_accel",
]

_HORIZON_EVENT = {
    "5d": ("fwd_ret_5", "fwd_max_ret_5", "fwd_max_dd_5", "up_10_5d"),
    "20d": ("fwd_ret_20", "fwd_max_ret_20", "fwd_max_dd_20", "up_25_20d"),
    "30d": ("fwd_ret_30", "fwd_max_ret_30", "fwd_max_dd_30", "up_50_30d"),
    "60d": ("fwd_ret_60", "fwd_max_ret_60", "fwd_max_dd_60", "up_50_60d"),
    "90d": ("fwd_ret_90", "fwd_max_ret_90", "fwd_max_dd_90", "up_50_90d"),
    "180d": ("fwd_ret_180", "fwd_max_ret_180", "fwd_max_dd_180", "up_100_180d"),
}


def _rule_masks(w: pd.DataFrame) -> dict[str, pd.Series]:
    g = w.get
    return {
        "rule1": (g("rvol_5_60") >= 3) & (g("ret_1m") > 0.20) & (g("vol_expansion") >= 1.5),
        "rule2": (g("breakout_20d") == 1) & (g("rvol_20_200") >= 2),
        "rule3": (g("dist_52w_high") >= -0.05) & (g("ret_3m") > 0) & (g("vol_accel") > 0),
    }


def apply_rules(con: duckdb.DuckDBPyConnection) -> dict:
    wide = load_wide(con)
    if wide.empty:
        raise RuntimeError("no panel data — run `marc panel build` first")
    wide = wide.reset_index()  # keep obs_id

    con.execute("DELETE FROM signal_outcome WHERE signal_id IN "
                "(SELECT signal_id FROM signal_log WHERE rule_version LIKE ?)", [RULE_VERSION_PREFIX + "%"])
    con.execute("DELETE FROM signal_log WHERE rule_version LIKE ?", [RULE_VERSION_PREFIX + "%"])

    masks = _rule_masks(wide)
    sig_rows, summary = [], {}
    for rname, mask in masks.items():
        mask = mask.fillna(False)
        hits = wide[mask]
        rv = f"{RULE_VERSION_PREFIX}:{rname}"
        for _, r in hits.iterrows():
            snap = {f: (None if pd.isna(r.get(f)) else round(float(r.get(f)), 6)) for f in _RULE_FEATURES}
            sig_rows.append({
                "security_id": int(r["security_id"]),
                "as_of_date": r["obs_date"].date(),
                "rule_version": rv,
                "feature_snapshot": json.dumps(snap),
                "obs_id": int(r["obs_id"]),
            })
        base_90 = wide["up_50_90d"].dropna().mean()
        hit_90 = hits["up_50_90d"].dropna().mean() if "up_50_90d" in hits else np.nan
        summary[rname] = {
            "n_signals": int(len(hits)),
            "p_up_50_90d": None if pd.isna(hit_90) else round(float(hit_90), 4),
            "base_up_50_90d": None if pd.isna(base_90) else round(float(base_90), 4),
        }

    if not sig_rows:
        log.warning("signals: no rule matched")
        return {"signals": 0, "by_rule": summary}

    sdf = pd.DataFrame(sig_rows)
    con.register("sdf", sdf[["security_id", "as_of_date", "rule_version", "feature_snapshot"]])
    con.execute(
        """
        INSERT INTO signal_log (security_id, as_of_date, rule_version, feature_snapshot, created_at)
        SELECT security_id, as_of_date, rule_version, feature_snapshot, now() FROM sdf
        """
    )
    con.unregister("sdf")

    # map back to signal_id and attach outcomes from target_panel
    got = con.execute(
        "SELECT signal_id, security_id, as_of_date, rule_version FROM signal_log WHERE rule_version LIKE ?",
        [RULE_VERSION_PREFIX + "%"],
    ).df()
    got["as_of_date"] = pd.to_datetime(got["as_of_date"]).dt.date
    key2sig = {(int(s), d, rv): int(sid)
               for sid, s, d, rv in zip(got["signal_id"], got["security_id"], got["as_of_date"], got["rule_version"])}

    tgt = con.execute("SELECT obs_id, target_name, value FROM target_panel").df()
    tgt_wide = tgt.pivot(index="obs_id", columns="target_name", values="value")

    out_rows = []
    for row in sig_rows:
        sig_id = key2sig.get((row["security_id"], row["as_of_date"], row["rule_version"]))
        if sig_id is None or row["obs_id"] not in tgt_wide.index:
            continue
        tr = tgt_wide.loc[row["obs_id"]]
        for hz, (rc, mr, dd, ev) in _HORIZON_EVENT.items():
            out_rows.append({
                "signal_id": sig_id, "horizon": hz,
                "realized_return": _get(tr, rc), "realized_max_return": _get(tr, mr),
                "realized_max_dd": _get(tr, dd), "realized_event": _get(tr, ev),
            })
    odf = pd.DataFrame(out_rows)
    con.register("odf", odf)
    con.execute(
        """
        INSERT INTO signal_outcome
            (signal_id, horizon, realized_return, realized_max_return, realized_max_dd, realized_event, evaluated_at)
        SELECT signal_id, horizon, realized_return, realized_max_return, realized_max_dd,
               CASE WHEN realized_event IS NULL THEN NULL WHEN realized_event >= 0.5 THEN TRUE ELSE FALSE END,
               now()
        FROM odf
        """
    )
    con.unregister("odf")

    log.info("signals: %d written; by_rule=%s", len(sig_rows), summary)
    return {"signals": len(sig_rows), "by_rule": summary}


def _get(series: pd.Series, col: str):
    if col not in series.index:
        return None
    v = series[col]
    return None if pd.isna(v) else float(v)
