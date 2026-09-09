"""Historiska analoger — hitta tidigare observationer som liknar en given situation.

Transparent och reproducerbar: standardiserat euklidiskt avstånd i feature-rymden
(z-score per feature, skattat på data FÖRE frågedatumet), k närmaste grannar,
sedan deras faktiska forward-utfall jämfört med en kontrollgrupp.

Anti-leakage (spec-brief §7):
- Frågevektorn kommer bara från ``feature_panel`` (känt vid t).
- Grannar måste ligga strikt före frågans datum.
- Frågebolaget utesluts helt som default (vi letar *andra* situationer).
- Ett grannutfall räknas bara med om det faktiskt är realiserat (annars NULL,
  och horisonten rapporterar ett lägre n).
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

# Default: pris/volym — robusta och INTE syntetiska.
ANALOGUE_FEATURES: list[str] = [
    "ret_1m", "ret_3m", "ret_6m",
    "rvol_5_60", "rvol_20_200", "vol_accel", "vol_trend_60d",
    "dist_52w_high", "rv_20d", "vol_expansion", "breakout_20d",
]
# Tillval: lägg till (syntetisk) attention. Märks i UI:t.
ANALOGUE_FEATURES_ATTENTION: list[str] = ANALOGUE_FEATURES + [
    "search_accel", "search_level_z", "forum_accel",
]

_HORIZONS = (5, 20, 30, 60, 90, 180)
_UP_EVENT = {5: "up_10_5d", 20: "up_25_20d", 30: "up_50_30d",
             60: "up_50_60d", 90: "up_50_90d", 180: "up_100_180d"}


def _wide(con: duckdb.DuckDBPyConnection, feature_names: list[str]) -> pd.DataFrame:
    """En rad per observation med meta + valda features. Rader med saknad feature droppas."""
    long = con.execute(
        """
        SELECT o.obs_id, o.security_id, o.obs_date, o.cap_segment_at_entry AS segment,
               fp.feature_name, fp.value
        FROM observation o JOIN feature_panel fp USING (obs_id)
        """
    ).df()
    if long.empty:
        return long
    piv = long.pivot_table(index=["obs_id", "security_id", "obs_date", "segment"],
                           columns="feature_name", values="value", aggfunc="last").reset_index()
    piv["obs_date"] = pd.to_datetime(piv["obs_date"])
    have = [f for f in feature_names if f in piv.columns]
    piv = piv.dropna(subset=have)
    return piv


def find_analogues(
    con: duckdb.DuckDBPyConnection,
    security_id: int,
    as_of_date=None,
    k: int = 40,
    feature_names: list[str] | None = None,
    exclude_query_security: bool = True,
    embargo_trading_days: int = 60,
    segment: str | None = None,
) -> pd.DataFrame:
    """k närmaste historiska grannar till ``security_id``s senaste observation
    (på eller före ``as_of_date``). Returnerar obs_id, security_id, obs_date, distance.
    """
    feats = feature_names or ANALOGUE_FEATURES
    piv = _wide(con, feats)
    if piv.empty:
        return pd.DataFrame(columns=["obs_id", "security_id", "obs_date", "distance"])
    have = [f for f in feats if f in piv.columns]

    q = piv[piv["security_id"] == security_id]
    if as_of_date is not None:
        q = q[q["obs_date"] <= pd.Timestamp(as_of_date)]
    if q.empty:
        return pd.DataFrame(columns=["obs_id", "security_id", "obs_date", "distance"])
    qrow = q.sort_values("obs_date").iloc[-1]
    qdate = qrow["obs_date"]

    # kandidater: strikt före frågedatum
    cand = piv[piv["obs_date"] < qdate].copy()
    if exclude_query_security:
        cand = cand[cand["security_id"] != security_id]
    else:
        cutoff = qdate - pd.Timedelta(days=int(embargo_trading_days * 1.5))
        cand = cand[(cand["security_id"] != security_id) | (cand["obs_date"] <= cutoff)]
    if segment in ("small", "mid"):
        cand = cand[cand["segment"] == segment]
    if len(cand) < 5:
        return pd.DataFrame(columns=["obs_id", "security_id", "obs_date", "distance"])

    # z-score per feature, skattat på kandidatpoolen (allt före frågedatum)
    mu = cand[have].mean()
    sd = cand[have].std(ddof=0).replace(0.0, np.nan)
    zc = (cand[have] - mu) / sd
    zq = (qrow[have].astype(float) - mu) / sd
    ok = zq.notna()
    used = [c for c in have if ok[c]]
    if not used:
        return pd.DataFrame(columns=["obs_id", "security_id", "obs_date", "distance"])

    d = np.sqrt(((zc[used].to_numpy() - zq[used].to_numpy()) ** 2).sum(axis=1) / len(used))
    cand = cand.assign(distance=d).dropna(subset=["distance"]).sort_values("distance")
    out = cand.head(k)[["obs_id", "security_id", "obs_date", "distance"]].reset_index(drop=True)
    out.attrs["query_obs_id"] = int(qrow["obs_id"])
    out.attrs["query_date"] = qdate
    out.attrs["features_used"] = used
    return out


def _targets_for(con: duckdb.DuckDBPyConnection, obs_ids: list[int]) -> pd.DataFrame:
    if not obs_ids:
        return pd.DataFrame()
    ph = ",".join("?" * len(obs_ids))
    t = con.execute(
        f"SELECT obs_id, target_name, value FROM target_panel WHERE obs_id IN ({ph})",
        obs_ids,
    ).df()
    if t.empty:
        return t
    return t.pivot_table(index="obs_id", columns="target_name", values="value", aggfunc="last")


def _summarise(tw: pd.DataFrame) -> dict:
    rows = {}
    for h in _HORIZONS:
        rc, mr, dd = f"fwd_ret_{h}", f"fwd_max_ret_{h}", f"fwd_max_dd_{h}"
        ev = _UP_EVENT[h]
        r = tw[rc].dropna() if rc in tw else pd.Series(dtype=float)
        mret = tw[mr].dropna() if mr in tw else pd.Series(dtype=float)
        mdd = tw[dd].dropna() if dd in tw else pd.Series(dtype=float)
        evs = tw[ev].dropna() if ev in tw else pd.Series(dtype=float)
        sus = tw[f"sustained_{h}"].dropna() if f"sustained_{h}" in tw else pd.Series(dtype=float)
        reversed_frac = None
        if len(mret) and rc in tw:
            paired = tw[[rc, mr]].dropna()
            if len(paired):
                gave_back = (paired[mr] >= 0.15) & (paired[rc] <= 0.0)
                reversed_frac = float(gave_back.mean())
        rows[h] = {
            "n": int(len(r)),
            "median_ret": float(r.median()) if len(r) else None,
            "mean_ret": float(r.mean()) if len(r) else None,
            "median_max_ret": float(mret.median()) if len(mret) else None,
            "median_max_dd": float(mdd.median()) if len(mdd) else None,
            "hit_rate": float(evs.mean()) if len(evs) else None,
            "event": _UP_EVENT[h],
            "sustained_frac": float(sus.mean()) if len(sus) else None,
            "reversed_frac": reversed_frac,
        }
    return rows


def analogue_outcomes(
    con: duckdb.DuckDBPyConnection,
    neighbours: pd.DataFrame,
    control_segment: str = "small",
) -> dict:
    """Aggregera grannarnas faktiska forward-utfall + en kontrollgrupp (hela segmentet)."""
    if neighbours is None or neighbours.empty:
        return {"n_analogues": 0}
    obs_ids = [int(x) for x in neighbours["obs_id"].tolist()]
    tw = _targets_for(con, obs_ids)

    ctrl_ids = [
        int(r[0]) for r in con.execute(
            "SELECT obs_id FROM observation WHERE cap_segment_at_entry = ?", [control_segment]
        ).fetchall()
    ]
    cw = _targets_for(con, ctrl_ids)

    per_h = _summarise(tw) if not tw.empty else {}
    ctrl_h = _summarise(cw) if not cw.empty else {}

    reached_50_90 = None
    if "up_50_90d" in tw.columns:
        s = tw["up_50_90d"].dropna()
        if len(s):
            reached_50_90 = (int(s.sum()), int(len(s)))

    # lift per horisont: grannarnas hit_rate / kontrollens
    for h, d in per_h.items():
        c = ctrl_h.get(h, {})
        d["control_hit_rate"] = c.get("hit_rate")
        d["control_median_ret"] = c.get("median_ret")
        d["lift"] = (
            d["hit_rate"] / c["hit_rate"]
            if d.get("hit_rate") is not None and c.get("hit_rate")
            else None
        )

    return {
        "n_analogues": int(len(neighbours)),
        "median_distance": float(neighbours["distance"].median()),
        "n_distinct_names": int(neighbours["security_id"].nunique()),
        "date_span": (neighbours["obs_date"].min().date().isoformat(),
                      neighbours["obs_date"].max().date().isoformat()),
        "horizons": per_h,
        "control_segment": control_segment,
        "reached_50_within_90d": reached_50_90,
    }
