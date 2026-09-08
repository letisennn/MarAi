"""Signaler — förregistrerade mönster som lyst, och hur det gått historiskt."""

from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import streamlit as st

from _data import (
    RULE_SV,
    active_signals,
    fwd90_box,
    is_synthetic,
    last_signal_date,
    latest_obs_date,
    recent_signal_log,
    signal_outcomes,
)

st.title("Signaler")

st.markdown(
    "En **signal** = ett bolag matchar ett av tre **förregistrerade mönster**. "
    "Inga skattade vikter, ingen score — villkoren är bestämda i förväg i "
    "`docs/experiments/E1.md`. Att en regel lyser säger *ingenting* om vad som "
    "kommer hända; det är ett mönster vars informationsvärde ska testas."
)
for rk, meta in RULE_SV.items():
    st.markdown(f"**{rk} — {meta['titel']}**  \n{meta['villkor']}")

if is_synthetic():
    st.warning("Syntetisk data — siffrorna nedan är exempel, inte resultat.")

d = latest_obs_date()
ls = last_signal_date()
st.caption(
    f"Senaste dataveckan i panelen: **{d:%Y-%m-%d}**"
    + (f" · senaste veckan någon regel lyste: **{ls:%Y-%m-%d}**" if ls is not None else "")
)

# --------------------------------------------------------- aktiva signaler
st.divider()
st.subheader("Aktiva signaler")
weeks = st.slider("Titta … veckor bakåt", min_value=1, max_value=26, value=8)
act = active_signals(weeks=weeks)

if act.empty:
    st.info(f"Ingen regel har lyst de senaste {weeks} veckorna.")
else:
    a = act.copy()
    a["Datum"] = pd.to_datetime(a["as_of_date"]).dt.strftime("%Y-%m-%d")

    def _snap(s: str) -> str:
        try:
            dd = json.loads(s) if s else {}
        except (TypeError, ValueError):
            return ""
        return ", ".join(f"{k}={round(v, 3)}" for k, v in dd.items() if v is not None)

    a["Mätvärden vid träff"] = a["feature_snapshot"].apply(_snap)
    a = a.rename(
        columns={"name": "Bolag", "country": "Land", "sector": "Sektor", "rule": "Regel"}
    )
    st.dataframe(
        a[["Datum", "Bolag", "Land", "Sektor", "Regel", "Mätvärden vid träff"]],
        hide_index=True,
        width="stretch",
        height=380,
    )
    st.caption(f"{len(a)} träffar · {a['Bolag'].nunique()} bolag. Öppna ett bolag i **Bolag i detalj**.")

# --------------------------------------------------------- historiskt utfall
st.divider()
st.subheader("Hur har signalerna gått historiskt?")
st.caption(
    "Träffkvot = andel signaler som följdes av en stor uppgång inom fönstret. "
    "Jämför med basnivån på **Start** (hur ofta det sker för ett slumpmässigt "
    "bolag samma vecka). Syntetisk data — illustrativt."
)
out = signal_outcomes()
if out.empty:
    st.info("Inga signalutfall. Kör `uv run marc signals`.")
else:
    horizon_order = ["5d", "20d", "30d", "60d", "90d", "180d"]
    out["horizon"] = pd.Categorical(out["horizon"], horizon_order, ordered=True)
    out = out.sort_values(["rule", "horizon"])
    tab = out.rename(
        columns={
            "rule": "Regel",
            "horizon": "Fönster",
            "n": "Antal",
            "avg_fwd_ret": "Snittavkastning",
            "hit_rate": "Träffkvot",
        }
    )
    st.dataframe(
        tab,
        hide_index=True,
        width="stretch",
        column_config={
            "Snittavkastning": st.column_config.NumberColumn(format="%+.3f"),
            "Träffkvot": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.plotly_chart(
        px.bar(
            tab, x="Fönster", y="Träffkvot", color="Regel", barmode="group",
            labels={"Träffkvot": "P(stor uppgång | signal)"}, height=340,
        ),
        width="stretch",
    )

box = fwd90_box()
if not box.empty:
    st.subheader("90-dagars avkastning — signaler vs alla observationer")
    st.plotly_chart(
        px.box(
            box, x="grp", y="r", points=False,
            labels={"r": "Avkastning 90 dagar", "grp": ""}, height=360,
        ),
        width="stretch",
    )

# --------------------------------------------------------- loggen
st.divider()
with st.expander("Signalloggen (senaste 100)"):
    lg = recent_signal_log(100)
    if lg.empty:
        st.write("Tom.")
    else:
        lg = lg.copy()
        lg["Datum"] = pd.to_datetime(lg["as_of_date"]).dt.strftime("%Y-%m-%d")
        lg = lg.rename(columns={"name": "Bolag", "rule": "Regel"})
        st.dataframe(lg[["Datum", "Bolag", "Regel"]], hide_index=True, width="stretch")
