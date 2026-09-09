"""Spara dagens radar-kandidater som ``discovery``-rader och fyll i utfall i
efterhand (paper trading-loopen, spec-brief §18).

``snapshot`` skriver en rad per topp-kandidat med en point-in-time
feature-ögonblicksbild, fas, motivering och analog-statistik. ``evaluate``
fyller ``discovery_outcome`` för de discoveries vars horisont hunnit passera,
uträknat från ``price_clean``.
"""

from __future__ import annotations

import json

import duckdb
import pandas as pd

from marc.config import get_logger, score_config
from marc.discovery.analogues import analogue_outcomes, find_analogues
from marc.discovery.phase import classify_phase

log = get_logger(__name__)

_HORIZON_DAYS = {"1d": 1, "5d": 5, "20d": 20, "30d": 30, "60d": 60, "90d": 90, "180d": 180}


def _latest_feature_frame(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(
        """
        WITH last_obs AS (SELECT security_id, max(obs_date) AS obs_date FROM observation GROUP BY 1)
        SELECT o.obs_id, o.security_id, o.obs_date, o.cap_segment_at_entry AS segment,
               fp.feature_name, fp.value
        FROM observation o
        JOIN last_obs l ON l.security_id = o.security_id AND l.obs_date = o.obs_date
        JOIN feature_panel fp USING (obs_id)
        """
    ).df()


def snapshot(con: duckdb.DuckDBPyConnection, top: int = 10, segment: str = "small") -> dict:
    """Skriv de ``top`` högst rankade kandidaterna (experimentell score) i en
    tidig/accelererande/hype-fas till ``discovery``."""
    from marc.score import assess  # lokal import: undviker cykel

    long = _latest_feature_frame(con)
    if long.empty:
        raise RuntimeError("ingen paneldata — kör `marc pipeline` först")
    wide = long.pivot_table(index=["obs_id", "security_id", "obs_date", "segment"],
                            columns="feature_name", values="value", aggfunc="last").reset_index()
    if segment in ("small", "mid"):
        wide = wide[wide["segment"] == segment]
    _meta = ("obs_id", "security_id", "obs_date", "segment")
    feat_cols = [c for c in wide.columns if c not in _meta]
    peers = wide.set_index("security_id")[feat_cols]

    rows = []
    for _, r in wide.iterrows():
        sid = int(r["security_id"])
        feats = {c: r[c] for c in feat_cols if pd.notna(r[c])}
        ph = classify_phase(feats)
        if ph.idx not in (2, 3, 4):
            continue
        b = assess(feats, peers, 0)
        rows.append((sid, r, feats, ph, b))
    rows.sort(key=lambda x: x[4].total, reverse=True)
    rows = rows[:top]
    if not rows:
        return {"written": 0}

    px = con.execute(
        "SELECT security_id, session_date, adj_close_sek FROM price_clean "
        "WHERE session_date = (SELECT max(session_date) FROM price_clean)"
    ).df().set_index("security_id")["adj_close_sek"].to_dict()

    nid = con.execute("SELECT coalesce(max(discovery_id), 0) FROM discovery").fetchone()[0]
    written = 0
    for sid, r, feats, ph, b in rows:
        exists = con.execute(
            "SELECT 1 FROM discovery WHERE security_id = ? AND as_of_date = ? AND source = 'daily_picks'",
            [sid, r["obs_date"]],
        ).fetchone()
        if exists:
            continue
        nid += 1
        nb = find_analogues(con, sid, k=40)
        astats = analogue_outcomes(con, nb) if not nb.empty else {"n_analogues": 0}
        con.execute(
            """
            INSERT INTO discovery
            (discovery_id, security_id, as_of_date, source, entry_price_sek,
             discovery_score, score_version, phase_key, phase_idx, feature_snapshot,
             reason, analogue_stats)
            VALUES (?, ?, ?, 'daily_picks', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [nid, sid, r["obs_date"], px.get(sid),
             round(b.total, 1), score_config().get("score_version", "prelim_v0.1"),
             ph.key, ph.idx, json.dumps({k: round(float(v), 6) for k, v in feats.items()}),
             _reason(feats, ph), json.dumps(_slim(astats), default=str)],
        )
        written += 1
    log.info("discovery snapshot: %d rows written", written)
    return {"written": written, "considered": len(rows)}


def _reason(feats: dict, ph) -> str:
    bits = [f"Fas: {ph.label.lower()}."]
    rv = feats.get("rvol_5_60")
    if rv is not None and abs(rv - 1) >= 0.15:
        bits.append(f"handel {abs(rv - 1) * 100:.0f} % {'över' if rv > 1 else 'under'} normalt")
    sa = feats.get("search_accel")
    if sa is not None and sa >= 0.15:
        bits.append(f"sökintresse {sa * 100:+.0f} % mot en månad sedan (syntetisk)")
    r1 = feats.get("ret_1m")
    if r1 is not None:
        bits.append(f"kurs {r1 * 100:+.0f} % senaste månaden")
    d = feats.get("dist_52w_high")
    if d is not None:
        bits.append(f"{abs(d) * 100:.0f} % under årshögsta" if d < -0.005 else "vid årshögsta")
    return "; ".join(bits)


def _slim(a: dict) -> dict:
    hz = a.get("horizons", {})
    return {
        "n_analogues": a.get("n_analogues", 0),
        "reached_50_within_90d": a.get("reached_50_within_90d"),
        "median_ret_30": hz.get(30, {}).get("median_ret"),
        "median_ret_90": hz.get(90, {}).get("median_ret"),
        "lift_90": hz.get(90, {}).get("lift"),
    }


def evaluate(con: duckdb.DuckDBPyConnection) -> dict:
    """Fyll ``discovery_outcome`` för discoveries vars horisont passerat."""
    disc = con.execute(
        "SELECT discovery_id, security_id, as_of_date, entry_price_sek FROM discovery"
    ).df()
    if disc.empty:
        return {"evaluated": 0}
    maxd = con.execute("SELECT max(session_date) FROM price_clean").fetchone()[0]
    written = 0
    for _, d in disc.iterrows():
        did = int(d["discovery_id"])
        p0 = d["entry_price_sek"]
        if p0 is None or pd.isna(p0):
            continue
        series = con.execute(
            "SELECT session_date, adj_close_sek, adj_high_sek, adj_low_sek FROM price_clean "
            "WHERE security_id = ? AND session_date >= ? ORDER BY session_date",
            [int(d["security_id"]), d["as_of_date"]],
        ).df()
        if series.empty:
            continue
        for hz, days in _HORIZON_DAYS.items():
            if len(series) <= days:
                continue
            window = series.iloc[1: days + 1]
            if window.empty or pd.Timestamp(d["as_of_date"]) + pd.Timedelta(days=days * 1.6) > pd.Timestamp(maxd):
                continue
            end_px = float(series.iloc[min(days, len(series) - 1)]["adj_close_sek"])
            con.execute(
                """
                INSERT OR REPLACE INTO discovery_outcome
                (discovery_id, horizon, realized_return, realized_max_return, realized_max_dd)
                VALUES (?, ?, ?, ?, ?)
                """,
                [did, hz, end_px / p0 - 1.0,
                 float(window["adj_high_sek"].max()) / p0 - 1.0,
                 float(window["adj_low_sek"].min()) / p0 - 1.0],
            )
            written += 1
    log.info("discovery evaluate: %d outcome rows", written)
    return {"evaluated": written}
