"""Marc AI — internal research app (v0.1 market baseline)."""

from __future__ import annotations

import streamlit as st

from _data import (
    db_exists,
    obs_date_bounds,
    pipeline_status,
    q,
    scalar,
)

st.set_page_config(page_title="Marc AI", page_icon="📈", layout="wide")

st.title("Marc AI — market baseline (v0.1)")
st.caption(
    "Private research tool. Nordic small-cap market-psychology & discovery engine. "
    "Follows `docs/marc_ai_spec.md`."
)

if not db_exists():
    st.warning("No database yet. Build it first:")
    st.code("uv run marc pipeline --source synthetic --reset", language="bash")
    st.stop()

src = scalar("SELECT source FROM ingestion_run ORDER BY run_id DESC LIMIT 1")
if src == "synthetic":
    st.info(
        "**Synthetic data.** Prices are deterministic pseudo-random paths, not market "
        "data — they exist to exercise and demo the pipeline. Swap in a real source "
        "(`--source yfinance`, or Börsdata/EODHD once signed off) before trusting any number."
    )

lo, hi = obs_date_bounds()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Securities", scalar("SELECT count(*) FROM security"))
c2.metric("Dead names (delisted/acq/bankrupt)",
          scalar("SELECT count(*) FROM security WHERE status <> 'listed'"))
c3.metric("Observations", f"{scalar('SELECT count(*) FROM observation'):,}")
c4.metric("Observation window", f"{lo:%Y-%m-%d} → {hi:%Y-%m-%d}" if lo is not None else "—")

st.subheader("Pipeline state")
left, right = st.columns([1, 1])
with left:
    st.dataframe(pipeline_status(), hide_index=True, width="stretch")
with right:
    runs = q(
        "SELECT run_id, source, started_at, status, n_in, n_rejected "
        "FROM ingestion_run ORDER BY run_id DESC LIMIT 5"
    )
    st.caption("Recent ingestion runs")
    st.dataframe(runs, hide_index=True, width="stretch")

st.subheader("E1a — unconditional large-move base rates (the control group)")
st.caption(
    "Share of weekly observations that hit each move within its window. Headline "
    "= `cap_segment_at_entry = 'small'`; `mid` (former small-caps that grew) shown for context."
)
br = q(
    """
    SELECT json_extract_string(subset, '$.event')   AS event,
           json_extract_string(subset, '$.segment') AS segment,
           round(value, 4)  AS rate,
           round(ci_low, 4) AS ci_low,
           round(ci_high, 4) AS ci_high,
           n_obs, n_events
    FROM experiment_result
    WHERE metric_name LIKE 'base_rate:%'
      AND json_extract_string(subset, '$.slice') = 'pooled'
    ORDER BY event, segment
    """
)
if br.empty:
    st.write("Run `marc stats` to populate experiment results.")
else:
    piv = br.pivot(index="event", columns="segment", values="rate")
    st.bar_chart(piv)
    st.dataframe(br, hide_index=True, width="stretch")

st.divider()
st.caption(
    "Pages: **Universe** (as-of membership) · **Security** (price / features / targets) · "
    "**Experiments** (E1 results) · **Signals** (pre-registered rules + outcomes)."
)
