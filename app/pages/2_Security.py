"""Single-security view — price, corporate actions, features, realised targets."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from _data import db_exists, q, securities

st.set_page_config(page_title="Security · Marc AI", page_icon="📈", layout="wide")
st.title("Security")

if not db_exists():
    st.warning("No database. Run `uv run marc pipeline --source synthetic --reset`.")
    st.stop()

secs = securities()
names = secs["name"].tolist()
pick = st.selectbox("Security", names, index=0)
row = secs[secs["name"] == pick].iloc[0]
sid = int(row["security_id"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Country", row["country"])
c2.metric("Sector", row["sector"] or "—")
c3.metric("Status", row["status"])
c4.metric("Delisting date", str(row["status_date"]) if pd.notna(row["status_date"]) else "—")

px_df = q(
    """
    SELECT session_date, close_local, adj_close_sek, volume, turnover_sek, market_cap_sek
    FROM price_clean WHERE security_id = ? ORDER BY session_date
    """,
    (sid,),
)
if px_df.empty:
    st.info("No price rows for this security.")
    st.stop()
px_df["session_date"] = pd.to_datetime(px_df["session_date"])

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.03)
fig.add_trace(go.Scatter(x=px_df["session_date"], y=px_df["adj_close_sek"],
                         name="adj close (SEK)", line=dict(width=1.4)), row=1, col=1)
fig.add_trace(go.Scatter(x=px_df["session_date"], y=px_df["close_local"],
                         name="raw close (local)", line=dict(width=1, dash="dot"),
                         opacity=0.5), row=1, col=1)
fig.add_trace(go.Bar(x=px_df["session_date"], y=px_df["volume"], name="volume",
                     marker=dict(color="#888")), row=2, col=1)
fig.update_layout(height=460, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
st.plotly_chart(fig, width="stretch")

ca = q(
    "SELECT action_type, ex_date, ratio, cash_amount, currency, source "
    "FROM corporate_action WHERE security_id = ? ORDER BY ex_date",
    (sid,),
)
lh = q(
    "SELECT status, market_segment, valid_from, valid_to, reason "
    "FROM listing_status_history WHERE security_id = ? ORDER BY valid_from",
    (sid,),
)
cc1, cc2 = st.columns(2)
cc1.caption("Corporate actions")
cc1.dataframe(ca, hide_index=True, width="stretch")
cc2.caption("Listing status history")
cc2.dataframe(lh, hide_index=True, width="stretch")

st.subheader("Features & realised targets at observation dates")
obs = q(
    """
    SELECT o.obs_id, o.obs_date, o.cap_segment_at_entry, o.market_cap_sek
    FROM observation o WHERE o.security_id = ? ORDER BY o.obs_date
    """,
    (sid,),
)
if obs.empty:
    st.info("This security has no observations (never in-universe during the study window).")
    st.stop()

feat = q("SELECT obs_id, feature_name, value FROM feature_panel WHERE obs_id IN "
         "(SELECT obs_id FROM observation WHERE security_id = ?)", (sid,))
tgt = q("SELECT obs_id, target_name, value FROM target_panel WHERE obs_id IN "
        "(SELECT obs_id FROM observation WHERE security_id = ?)", (sid,))
fw = feat.pivot(index="obs_id", columns="feature_name", values="value")
tw = tgt.pivot(index="obs_id", columns="target_name", values="value")
wide = obs.set_index("obs_id").join(fw).join(tw)
wide["obs_date"] = pd.to_datetime(wide["obs_date"])

fcols = sorted([c for c in fw.columns])
fsel = st.multiselect("Plot features over time", fcols,
                      default=[c for c in ["ret_3m", "rvol_5_60", "vol_expansion"] if c in fcols])
if fsel:
    st.line_chart(wide.set_index("obs_date")[fsel])

tcols = [c for c in ["fwd_ret_20", "fwd_ret_90", "fwd_max_ret_90", "fwd_max_dd_90"] if c in tw.columns]
if tcols:
    st.caption("Realised forward outcomes (future data — shown for inspection)")
    st.line_chart(wide.set_index("obs_date")[tcols])

with st.expander("Raw observation table"):
    st.dataframe(wide.reset_index(drop=True), width="stretch")
