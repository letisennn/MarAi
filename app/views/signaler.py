"""Signaler — vilka bolag matchar ett förregistrerat mönster, och vad historiken visar."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from _data import (
    EVENT_SHORT,
    RULE_SV,
    active_signals,
    is_synthetic,
    last_signal_date,
    latest_obs_date,
    recent_signal_log,
    rule_outcome_stats,
)

st.title("Signaler")

st.markdown(
    "En **signal** = ett bolag matchar ett av tre **förregistrerade mönster**. "
    "Inga skattade vikter, ingen poäng — villkoren är bestämda i förväg. Att en "
    "regel lyser säger *ingenting säkert* om vad som kommer hända; det är ett "
    "mönster vars informationsvärde ska testas."
)
for meta in RULE_SV.values():
    st.markdown(f"**{meta['titel']}**  \n{meta['villkor']}")

if is_synthetic():
    st.warning("Syntetisk data — siffrorna nedan är historik på påhittade kurser, inte resultat.")

d = latest_obs_date()
ls = last_signal_date()
st.caption(
    f"Senaste dataveckan i panelen: **{d:%Y-%m-%d}**"
    + (f" · senaste veckan någon regel lyste: **{ls:%Y-%m-%d}**" if ls is not None else "")
)

# --------------------------------------------------------- aktiva signaler
st.divider()
st.subheader("Vilka bolag lyser just nu?")
weeks = st.slider("Titta … veckor bakåt", min_value=1, max_value=26, value=8)
act = active_signals(weeks=weeks)

if act.empty:
    st.info(f"Ingen regel har lyst de senaste {weeks} veckorna.")
else:
    a = act.copy()
    a["Datum"] = pd.to_datetime(a["as_of_date"]).dt.strftime("%Y-%m-%d")
    a["Mönster"] = a["rule"].map({k: v["titel"] for k, v in RULE_SV.items()}).fillna(a["rule"])
    a = a.rename(columns={"name": "Bolag", "country": "Land", "sector": "Sektor"})
    st.dataframe(
        a[["Datum", "Bolag", "Land", "Sektor", "Mönster"]],
        hide_index=True,
        width="stretch",
        height=360,
    )
    st.caption(
        f"{len(a)} träffar · {a['Bolag'].nunique()} bolag. "
        "Öppna ett bolag under **Bolag i detalj** för hela genomgången."
    )

# --------------------------------------------------------- historik
st.divider()
st.subheader("Vad har hänt historiskt efter varje mönster?")
st.caption(
    "För varje mönster: hur ofta en stor uppgång följde inom olika tidsfönster "
    "(**blått**), jämfört med hur ofta samma uppgång sker för vilket bolag som "
    "helst samma vecka (**grått**). Historik på syntetisk data — inte en prognos."
)

stats = rule_outcome_stats()
if stats.empty:
    st.info("Ingen signalhistorik. Kör `uv run marc signals`.")
else:
    for rk, meta in RULE_SV.items():
        rs = stats[stats["rule"] == rk]
        if rs.empty:
            continue
        n = int(rs["n"].iloc[0])
        with st.container(border=True):
            st.markdown(f"**{meta['titel']}**  ·  {n} historiska träffar")
            if n < 20:
                st.caption("För få träffar för att tolka utfallet.")
                continue
            long_rows = []
            for _, r in rs.iterrows():
                lbl = EVENT_SHORT.get(r["horizon"], r["horizon"])
                long_rows.append({"x": lbl, "grp": "Efter signalen", "andel": r["hit_rate"]})
                long_rows.append({"x": lbl, "grp": "Normalt", "andel": r["base_rate"]})
            cdf = pd.DataFrame(long_rows)
            fig = px.bar(
                cdf, x="x", y="andel", color="grp", barmode="group",
                color_discrete_map={"Efter signalen": "#2f6fed", "Normalt": "#b7bec9"},
                labels={"andel": "andel av fallen", "x": "", "grp": ""},
            )
            fig.update_yaxes(tickformat=".0%")
            fig.update_layout(height=280, margin=dict(l=0, r=0, t=6, b=0), legend=dict(orientation="h"))
            st.plotly_chart(fig, width="stretch")
            r90 = rs[rs["horizon"] == "90d"]
            if not r90.empty:
                st.caption(
                    f"Största rörelse inom ~4 månader efteråt (median): "
                    f"upp {r90['med_max_ret'].iloc[0]:+.0%}, ned {r90['med_max_dd'].iloc[0]:+.0%}."
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
        lg["Mönster"] = lg["rule"].map({k: v["titel"] for k, v in RULE_SV.items()}).fillna(lg["rule"])
        lg = lg.rename(columns={"name": "Bolag"})
        st.dataframe(lg[["Datum", "Bolag", "Mönster"]], hide_index=True, width="stretch")
