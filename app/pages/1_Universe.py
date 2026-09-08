"""Point-in-time universe membership."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from _data import db_exists, members_asof, obs_date_bounds, q, universe_name

st.set_page_config(page_title="Universe · Marc AI", page_icon="📈", layout="wide")
st.title("Universe — as of a date")

if not db_exists():
    st.warning("No database. Run `uv run marc pipeline --source synthetic --reset`.")
    st.stop()

lo, hi = obs_date_bounds()
default = hi.date() if hi is not None else pd.Timestamp.today().date()
on = st.date_input("Membership as of", value=default,
                   min_value=lo.date() if lo is not None else None,
                   max_value=hi.date() if hi is not None else None)

st.caption(f"Universe `{universe_name()}` — evaluated monthly, point-in-time market cap. "
           "Admission ≤ SEK 1.7bn; names that grow past it are retained and tagged **mid**.")

m = members_asof(pd.Timestamp(on))
if m.empty:
    st.info("No members on that date.")
    st.stop()

m["segment"] = m["market_cap_sek"].apply(lambda x: "small" if pd.notna(x) and x <= 1.7e9 else "mid")
m["market_cap_MSEK"] = (m["market_cap_sek"] / 1e6).round(0)
m["turnover_kSEK"] = (m["turnover_sek"] / 1e3).round(0)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Members", len(m))
c2.metric("small", int((m["segment"] == "small").sum()))
c3.metric("mid (grew out)", int((m["segment"] == "mid").sum()))
c4.metric("Countries", m["country"].nunique())

st.dataframe(
    m[["name", "country", "sector", "status", "segment", "market_cap_MSEK", "turnover_kSEK",
       "valid_from", "valid_to"]],
    hide_index=True, width="stretch",
)

st.subheader("Universe size over time")
size = q(
    """
    WITH months AS (
        SELECT DISTINCT date_trunc('month', obs_date) AS m FROM observation
    )
    SELECT months.m AS month,
           o.cap_segment_at_entry AS segment,
           count(DISTINCT o.security_id) AS n
    FROM months
    JOIN observation o ON date_trunc('month', o.obs_date) = months.m
    GROUP BY 1, 2 ORDER BY 1, 2
    """
)
if not size.empty:
    fig = px.area(size, x="month", y="n", color="segment",
                  labels={"n": "securities", "month": ""})
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
