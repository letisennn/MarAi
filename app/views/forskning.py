"""Forskning (E1) — bär enkla pris- och volymmått information om framtida rörelser?"""

from __future__ import annotations

import json

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from _data import e1_experiment, e1_results, is_synthetic

st.title("Forskning — Experiment E1")

st.markdown(
    "**Forskningsfrågan:** bär enkla pris- och volymmått någon statistiskt "
    "meningsfull information om framtida avkastning och stora rörelser i "
    "nordiska småbolag? Upptäckt sker på 2020–2024; en **holdout** "
    "(2025-01→2026-06) utvärderas *en gång*. Nollresultat och trasiga regler "
    "sparas, de göms inte. \"Nej / svagt\" är ett godtagbart svar."
)
if is_synthetic():
    st.warning(
        "Syntetisk data: de syntetiska kurserna har inbyggd drift och "
        "\"attention-bursts\", så momentum ser ut att fungera — det är cirkulärt. "
        "Den här sidan visar att maskineriet ger rätt *form* på utdata."
    )


def _loads(s):
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s) if s else {}
    except (TypeError, ValueError):
        return {}


exp = e1_experiment()
if exp.empty:
    st.info("Inget E1-experiment ännu. Kör `uv run marc stats`.")
    st.stop()

eid = int(exp.loc[0, "experiment_id"])
with st.expander("Förregistrering / spec (docs/experiments/E1.md)"):
    st.json(_loads(exp.loc[0, "spec"]))

res = e1_results(eid)
res["kind"] = res["metric_name"].str.split(":").str[0]
res["S"] = res["subset"].apply(_loads)
res["P"] = res["params"].apply(_loads)


def field(df, col, key):
    return df[col].apply(lambda d: d.get(key))


tabs = st.tabs(
    [
        "Basnivåer (E1a)",
        "Signalstyrka per mått (E1b)",
        "Kvintilspridning (E1b)",
        "Träffökning / lift (E1b)",
        "Fama-MacBeth (E1c)",
    ]
)

with tabs[0]:
    st.caption(
        "Hur ofta en stor uppgång sker **oavsett** mått — kontrollgruppen. Allt "
        "annat mäts mot den här nivån."
    )
    br = res[res["kind"] == "base_rate"].copy()
    for k in ("event", "segment", "slice", "year"):
        br[k] = field(br, "S", k)
    pooled = br[br["slice"] == "pooled"]
    piv = pooled.pivot_table(index="event", columns="segment", values="value")
    st.plotly_chart(
        px.bar(piv, barmode="group", labels={"value": "P(uppgång)", "event": "Uppgång"}, height=340),
        width="stretch",
    )
    st.dataframe(
        pooled[["event", "segment", "value", "ci_low", "ci_high", "n_obs", "n_events"]]
        .sort_values(["event", "segment"])
        .rename(
            columns={
                "event": "Uppgång", "segment": "Segment", "value": "Andel",
                "ci_low": "KI låg", "ci_high": "KI hög",
                "n_obs": "Antal obs", "n_events": "Antal träffar",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    byyr = br[(br["slice"] == "year") & (br["segment"] == "small")].sort_values("year")
    if not byyr.empty:
        st.caption("Per år (small):")
        st.plotly_chart(
            px.line(byyr, x="year", y="value", color="event", markers=True,
                    labels={"value": "P(uppgång)", "year": "År"}, height=320),
            width="stretch",
        )

with tabs[1]:
    st.caption(
        "Rank-IC = korrelationen mellan ett måtts rangordning en vecka och "
        "avkastningen framåt. ~0 = ingen information. Felstaplar = 95 % "
        "block-bootstrap-intervall; korsar de noll bär måttet inget."
    )
    ic = res[res["kind"] == "ic_mean"].copy()
    ic["feature"] = ic["metric_name"].str.split(":").str[1]
    ic["target"] = ic["metric_name"].str.split(":").str[2]
    ic["split"] = field(ic, "S", "split")
    ic["t_stat"] = field(ic, "P", "t_stat")
    split = st.radio("Period", sorted(ic["split"].dropna().unique()), horizontal=True)
    d = ic[ic["split"] == split].sort_values("value")
    fig = go.Figure(
        go.Bar(
            x=d["value"],
            y=d["feature"] + " · " + d["target"],
            orientation="h",
            error_x=dict(
                type="data", symmetric=False,
                array=(d["ci_high"] - d["value"]).clip(lower=0),
                arrayminus=(d["value"] - d["ci_low"]).clip(lower=0),
            ),
        )
    )
    fig.add_vline(x=0, line_color="#999")
    fig.update_layout(
        height=24 * len(d) + 60, margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="genomsnittlig veckovis rank-IC (95 % block-bootstrap)",
    )
    st.plotly_chart(fig, width="stretch")
    st.dataframe(
        d[["feature", "target", "value", "ci_low", "ci_high", "t_stat", "n_obs"]]
        .rename(columns={"feature": "Mått", "target": "Utfall", "value": "IC"}),
        hide_index=True,
        width="stretch",
    )

with tabs[2]:
    st.caption(
        "Dela in bolagen i femtedelar (kvintiler) efter ett mått; visa "
        "genomsnittligt utfall per femtedel. Q5−Q1 = skillnaden mellan högsta "
        "och lägsta femtedelen."
    )
    qs = res[res["kind"] == "q5_q1_spread"].copy()
    qs["feature"] = qs["metric_name"].str.split(":").str[1]
    qs["target"] = qs["metric_name"].str.split(":").str[2]
    qs["split"] = field(qs, "S", "split")
    qs["q_means"] = field(qs, "S", "q_means")
    sp = st.radio("Period ", sorted(qs["split"].dropna().unique()), horizontal=True, key="qsp")
    dq = qs[qs["split"] == sp]
    if not dq.empty:
        feat = st.selectbox("Mått", sorted(dq["feature"].unique()))
        tgt = st.selectbox("Utfall", sorted(dq["target"].unique()))
        rowm = dq[(dq["feature"] == feat) & (dq["target"] == tgt)]
        if not rowm.empty and rowm.iloc[0]["q_means"]:
            qm = rowm.iloc[0]["q_means"]
            st.plotly_chart(
                px.bar(
                    x=[f"Q{i + 1}" for i in range(len(qm))], y=qm,
                    labels={"x": "femtedel av måttet", "y": f"snitt {tgt}"}, height=340,
                ),
                width="stretch",
            )
        st.dataframe(
            dq[["feature", "target", "value"]]
            .rename(columns={"feature": "Mått", "target": "Utfall", "value": "Q5 − Q1"})
            .sort_values("Q5 − Q1"),
            hide_index=True,
            width="stretch",
        )

with tabs[3]:
    st.caption(
        "Lift = P(stor uppgång | måttet i högsta femtedelen) delat med "
        "P(stor uppgång | alla). 1,0 = ingen effekt; > 1 = uppgången är "
        "vanligare i toppfemtedelen."
    )
    lf = res[res["kind"] == "lift_top_quintile"].copy()
    lf["feature"] = lf["metric_name"].str.split(":").str[1]
    lf["event"] = lf["metric_name"].str.split(":").str[2]
    lf["split"] = field(lf, "S", "split")
    lf["p_cond"] = field(lf, "S", "p_cond")
    lf["p_base"] = field(lf, "S", "p_base")
    if not lf.empty:
        spl = st.radio("Period", sorted(lf["split"].dropna().unique()), horizontal=True, key="lsp")
        ev = st.selectbox("Uppgång", sorted(lf["event"].unique()))
        dl = lf[(lf["split"] == spl) & (lf["event"] == ev)].sort_values("value", ascending=False)
        fig = px.bar(dl, x="feature", y="value", height=340,
                     labels={"value": "lift", "feature": "Mått"})
        fig.add_hline(y=1.0, line_color="#999")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(
            dl[["feature", "value", "p_cond", "p_base", "n_obs", "n_events"]]
            .rename(columns={"feature": "Mått", "value": "Lift"}),
            hide_index=True,
            width="stretch",
        )

with tabs[4]:
    st.caption(
        "Veckovisa tvärsnittsregressioner av avkastning 20 dagar framåt på "
        "standardiserade mått; snittet av koefficienterna. Positivt = måttet "
        "hänger ihop med högre avkastning framåt. Enkla t-värden (Newey-West "
        "är en TODO)."
    )
    fm = res[res["kind"] == "fm_beta"].copy()
    if fm.empty:
        st.info("Fama-MacBeth gav inga användbara veckor.")
    else:
        fm["feature"] = fm["metric_name"].str.split(":").str[1]
        fm = fm[fm["feature"] != "intercept"].sort_values("value")
        fig = go.Figure(
            go.Bar(
                x=fm["value"], y=fm["feature"], orientation="h",
                error_x=dict(
                    type="data", symmetric=False,
                    array=(fm["ci_high"] - fm["value"]).clip(lower=0),
                    arrayminus=(fm["value"] - fm["ci_low"]).clip(lower=0),
                ),
            )
        )
        fig.add_vline(x=0, line_color="#999")
        fig.update_layout(
            height=24 * len(fm) + 60, margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="snittkoefficient på standardiserat mått → avkastning 20 dgr",
        )
        st.plotly_chart(fig, width="stretch")
        st.dataframe(
            fm[["feature", "value", "ci_low", "ci_high", "n_obs"]]
            .rename(columns={"feature": "Mått", "value": "Koefficient"}),
            hide_index=True,
            width="stretch",
        )
