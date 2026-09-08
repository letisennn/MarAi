"""Experiment E1 — base rates, univariate IC, quintile spreads, Fama-MacBeth."""

from __future__ import annotations

import json

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from _data import db_exists, q

st.set_page_config(page_title="Experiments · Marc AI", page_icon="📈", layout="wide")
st.title("Experiment E1 — does simple price/volume carry information?")

if not db_exists():
    st.warning("No database. Run `uv run marc pipeline --source synthetic --reset`.")
    st.stop()


def _loads(s):
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s) if s else {}
    except (TypeError, ValueError):
        return {}


exp = q("SELECT experiment_id, name, hypothesis, spec, created_at FROM experiment WHERE name = 'E1' "
        "ORDER BY experiment_id DESC LIMIT 1")
if exp.empty:
    st.info("No E1 experiment yet. Run `uv run marc stats`.")
    st.stop()
eid = int(exp.loc[0, "experiment_id"])
st.caption(exp.loc[0, "hypothesis"])
with st.expander("Pre-registration / spec (docs/experiments/E1.md)"):
    st.json(_loads(exp.loc[0, "spec"]))
    st.markdown(
        "Headline results use `cap_segment_at_entry = 'small'`. Discovery 2020–2024; "
        "**holdout 2025-01→2026-06 evaluated once**. Nulls and failed rules are stored, "
        "not hidden. BH-FDR multiple-testing control is a documented TODO."
    )

res = q("SELECT metric_name, subset, value, ci_low, ci_high, n_obs, n_events, is_out_of_sample, params "
        "FROM experiment_result WHERE experiment_id = ?", (eid,))
res["kind"] = res["metric_name"].str.split(":").str[0]
res["S"] = res["subset"].apply(_loads)
res["P"] = res["params"].apply(_loads)


def field(df, col, key):
    return df[col].apply(lambda d: d.get(key))


tabs = st.tabs(["Base rates (E1a)", "Univariate IC (E1b)", "Quintile spread (E1b)",
                "Event lift (E1b)", "Fama-MacBeth (E1c)"])

with tabs[0]:
    br = res[res["kind"] == "base_rate"].copy()
    for k in ("event", "segment", "slice", "year"):
        br[k] = field(br, "S", k)
    pooled = br[br["slice"] == "pooled"]
    piv = pooled.pivot_table(index="event", columns="segment", values="value")
    st.plotly_chart(px.bar(piv, barmode="group", labels={"value": "P(event)"}, height=340),
                    width="stretch")
    st.dataframe(pooled[["event", "segment", "value", "ci_low", "ci_high", "n_obs", "n_events"]]
                 .sort_values(["event", "segment"]), hide_index=True, width="stretch")
    byyr = br[(br["slice"] == "year") & (br["segment"] == "small")].sort_values("year")
    if not byyr.empty:
        st.caption("By year (small):")
        st.plotly_chart(px.line(byyr, x="year", y="value", color="event", markers=True, height=320),
                        width="stretch")

with tabs[1]:
    ic = res[res["kind"] == "ic_mean"].copy()
    ic["feature"] = ic["metric_name"].str.split(":").str[1]
    ic["target"] = ic["metric_name"].str.split(":").str[2]
    ic["split"] = field(ic, "S", "split")
    ic["t_stat"] = field(ic, "P", "t_stat")
    split = st.radio("Split", sorted(ic["split"].dropna().unique()), horizontal=True)
    d = ic[ic["split"] == split].sort_values("value")
    fig = go.Figure(go.Bar(
        x=d["value"], y=d["feature"] + " · " + d["target"], orientation="h",
        error_x=dict(type="data", symmetric=False,
                     array=(d["ci_high"] - d["value"]).clip(lower=0),
                     arrayminus=(d["value"] - d["ci_low"]).clip(lower=0)),
    ))
    fig.add_vline(x=0, line_color="#999")
    fig.update_layout(height=24 * len(d) + 60, margin=dict(l=0, r=0, t=10, b=0),
                      xaxis_title="mean weekly rank IC (95% block-bootstrap CI)")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(d[["feature", "target", "value", "ci_low", "ci_high", "t_stat", "n_obs"]],
                 hide_index=True, width="stretch")

with tabs[2]:
    qs = res[res["kind"] == "q5_q1_spread"].copy()
    qs["feature"] = qs["metric_name"].str.split(":").str[1]
    qs["target"] = qs["metric_name"].str.split(":").str[2]
    qs["split"] = field(qs, "S", "split")
    qs["q_means"] = field(qs, "S", "q_means")
    sp = st.radio("Split ", sorted(qs["split"].dropna().unique()), horizontal=True, key="qsp")
    dq = qs[qs["split"] == sp]
    if not dq.empty:
        feat = st.selectbox("Feature", sorted(dq["feature"].unique()))
        tgt = st.selectbox("Target", sorted(dq["target"].unique()))
        rowm = dq[(dq["feature"] == feat) & (dq["target"] == tgt)]
        if not rowm.empty and rowm.iloc[0]["q_means"]:
            qm = rowm.iloc[0]["q_means"]
            st.plotly_chart(px.bar(x=[f"Q{i+1}" for i in range(len(qm))], y=qm,
                                   labels={"x": "feature quintile", "y": f"mean {tgt}"}, height=340),
                            width="stretch")
        st.dataframe(dq[["feature", "target", "value"]].rename(columns={"value": "Q5_minus_Q1"})
                     .sort_values("Q5_minus_Q1"), hide_index=True, width="stretch")

with tabs[3]:
    lf = res[res["kind"] == "lift_top_quintile"].copy()
    lf["feature"] = lf["metric_name"].str.split(":").str[1]
    lf["event"] = lf["metric_name"].str.split(":").str[2]
    lf["split"] = field(lf, "S", "split")
    lf["p_cond"] = field(lf, "S", "p_cond")
    lf["p_base"] = field(lf, "S", "p_base")
    if not lf.empty:
        spl = st.radio("Split", sorted(lf["split"].dropna().unique()), horizontal=True, key="lsp")
        ev = st.selectbox("Event", sorted(lf["event"].unique()))
        dl = lf[(lf["split"] == spl) & (lf["event"] == ev)].sort_values("value", ascending=False)
        st.caption("lift = P(event | feature in top quintile) / P(event | all)")
        fig = px.bar(dl, x="feature", y="value", height=340, labels={"value": "lift"})
        fig.add_hline(y=1.0, line_color="#999")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(dl[["feature", "value", "p_cond", "p_base", "n_obs", "n_events"]],
                     hide_index=True, width="stretch")

with tabs[4]:
    fm = res[res["kind"] == "fm_beta"].copy()
    if fm.empty:
        st.info("Fama-MacBeth produced no usable weeks.")
    else:
        fm["feature"] = fm["metric_name"].str.split(":").str[1]
        fm = fm[fm["feature"] != "intercept"].sort_values("value")
        fig = go.Figure(go.Bar(
            x=fm["value"], y=fm["feature"], orientation="h",
            error_x=dict(type="data", symmetric=False,
                         array=(fm["ci_high"] - fm["value"]).clip(lower=0),
                         arrayminus=(fm["value"] - fm["ci_low"]).clip(lower=0)),
        ))
        fig.add_vline(x=0, line_color="#999")
        fig.update_layout(height=24 * len(fm) + 60, margin=dict(l=0, r=0, t=10, b=0),
                          xaxis_title="avg weekly coef on standardised feature → fwd_ret_20")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(fm[["feature", "value", "ci_low", "ci_high", "n_obs"]],
                     hide_index=True, width="stretch")
