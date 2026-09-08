"""Signals — pre-registered E1d rules and their realised outcomes."""

from __future__ import annotations

import json

import plotly.express as px
import streamlit as st

from _data import db_exists, q

st.set_page_config(page_title="Signals · Marc AI", page_icon="📈", layout="wide")
st.title("Signals — pre-registered rules (E1d)")

if not db_exists():
    st.warning("No database. Run `uv run marc pipeline --source synthetic --reset`.")
    st.stop()

st.markdown(
    "Rules are **pre-registered** in `docs/experiments/E1.md` §E1d — no fitted weights, "
    "no score. Each match is logged with its feature snapshot; outcomes are joined from "
    "`target_panel`. On synthetic data these numbers are illustrative only."
)
st.code(
    "rule1: rvol_5_60 >= 3  AND  ret_1m > 0.20  AND  vol_expansion >= 1.5\n"
    "rule2: breakout_20d = 1  AND  rvol_20_200 >= 2\n"
    "rule3: dist_52w_high >= -0.05  AND  ret_3m > 0  AND  vol_accel > 0",
    language="text",
)

log = q(
    """
    SELECT sl.signal_id, s.name, sl.as_of_date, sl.rule_version, sl.feature_snapshot
    FROM signal_log sl JOIN security s USING (security_id)
    ORDER BY sl.as_of_date DESC
    """
)
if log.empty:
    st.info("No signals. Run `uv run marc signals`.")
    st.stop()
log["rule"] = log["rule_version"].str.split(":").str[-1]

rules = sorted(log["rule"].unique())
pick = st.multiselect("Rules", rules, default=rules)
flt = log[log["rule"].isin(pick)]

c1, c2, c3 = st.columns(3)
c1.metric("Signals", len(flt))
c2.metric("Distinct securities", flt["name"].nunique())
c3.metric("Date range", f"{flt['as_of_date'].min()} → {flt['as_of_date'].max()}")

st.subheader("Outcome vs base rate")
out = q(
    """
    WITH base AS (
        SELECT json_extract_string(subset, '$.event') AS event, value AS base_rate
        FROM experiment_result
        WHERE metric_name LIKE 'base_rate:%'
          AND json_extract_string(subset, '$.segment') = 'small'
          AND json_extract_string(subset, '$.slice')   = 'pooled'
    )
    SELECT split_part(sl.rule_version, ':', -1) AS rule,
           so.horizon,
           count(*)                                                   AS n,
           round(avg(so.realized_return), 4)                          AS avg_fwd_ret,
           round(avg(CASE WHEN so.realized_event THEN 1.0 ELSE 0.0 END), 4) AS hit_rate
    FROM signal_outcome so
    JOIN signal_log sl USING (signal_id)
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
)
horizon_order = ["5d", "20d", "30d", "60d", "90d", "180d"]
out["horizon"] = out["horizon"].astype("category").cat.set_categories(horizon_order, ordered=True)
out = out[out["rule"].isin(pick)].sort_values(["rule", "horizon"])
st.dataframe(out, hide_index=True, width="stretch")

st.plotly_chart(
    px.bar(out, x="horizon", y="hit_rate", color="rule", barmode="group",
           labels={"hit_rate": "P(large-move event | signal)"}, height=340),
    width="stretch",
)

st.subheader("Realised 90-day forward return — signals vs all observations")
dist = q(
    """
    SELECT 'signal ('||split_part(sl.rule_version, ':', -1)||')' AS grp, so.realized_return AS r
    FROM signal_outcome so JOIN signal_log sl USING (signal_id)
    WHERE so.horizon = '90d' AND so.realized_return IS NOT NULL
    UNION ALL
    SELECT 'all observations' AS grp, value AS r
    FROM target_panel WHERE target_name = 'fwd_ret_90' AND value IS NOT NULL
    """
)
dist = dist[dist["grp"].apply(lambda g: g == "all observations" or any(f"({r})" in g for r in pick))]
st.plotly_chart(
    px.box(dist, x="grp", y="r", points=False, labels={"r": "fwd_ret_90", "grp": ""}, height=360),
    width="stretch",
)

st.subheader("Signal log")
show = flt.copy()
show["features"] = show["feature_snapshot"].apply(
    lambda s: ", ".join(f"{k}={v}" for k, v in json.loads(s).items() if v is not None)
)
st.dataframe(show[["name", "as_of_date", "rule", "features"]], hide_index=True, width="stretch")
