"""Signaler — vilka bolag matchar ett förregistrerat mönster, och vad historiken visar."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from _data import (
    EVENT_SHORT,
    RULE_SV,
    active_signals,
    best_rule_horizon,
    is_synthetic,
    last_signal_date,
    latest_obs_date,
    recent_signal_log,
    rule_outcome_stats,
)


def _horizon_caption(rk: str) -> str:
    bh = best_rule_horizon(rk)
    if bh is None:
        return "⏱ Tidshorisont: inget tidsfönster (1 v–9 mån) visar ännu en tillförlitlig avvikelse — obevisat."
    return f"⏱ Tidshorisont: **{bh['label']}** (kortaste fönster med tillförlitlig avvikelse, {bh['n']} träffar)"


st.title("Signaler")
st.warning(
    "Forskarvy. Träffkvoterna här räknas från ett 5-dagarsmedel (P0), inte från köpkursen — det "
    "överdriver vinsten för mönster som fångar bolag efter en uppgång (utbrott). För vad ett läge "
    "betytt för en *köpare*: se guiderna på Market Radar och Rörelser & utbrott (E1e).",
    icon="⚠️",
)

st.markdown(
    "En **signal** = ett bolag matchar ett av fyra **förregistrerade mönster**. "
    "Inga skattade vikter, ingen poäng — villkoren är bestämda i förväg. Att en "
    "regel lyser säger *ingenting säkert* om vad som kommer hända; det är ett "
    "mönster vars informationsvärde ska testas. Tidshorisonten nedan är INTE en "
    "rekommenderad hålltid — olika mönster löser sig olika fort, så den är räknad "
    "fram per mönster, inte samma tal för alla."
)
for rk, meta in RULE_SV.items():
    st.markdown(f"**{meta['titel']}**  \n{meta['villkor']}  \n{_horizon_caption(rk)}")

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
    a["Signal utfärdad"] = pd.to_datetime(a["as_of_date"]).dt.strftime("%Y-%m-%d")
    a["Mönster"] = a["rule"].map({k: v["titel"] for k, v in RULE_SV.items()}).fillna(a["rule"])
    _hz_by_rule = {rk: (best_rule_horizon(rk) or {}).get("label", "obevisat ännu") for rk in RULE_SV}
    a["Tidshorisont"] = a["rule"].map(_hz_by_rule)
    a = a.rename(columns={"name": "Bolag", "country": "Land", "sector": "Sektor"})
    st.dataframe(
        a[["Signal utfärdad", "Bolag", "Land", "Sektor", "Mönster", "Tidshorisont"]],
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
    "Tidshorisonten nedan är räknad fram per mönster — det kortaste tidsfönstret "
    "(1 vecka–9 månader) där mönstret historiskt visat en tillförlitlig avvikelse "
    "från basnivån. Inte en rekommenderad hålltid. Alla tidsfönster finns i grafen "
    "under varje mönster."
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
            bh = best_rule_horizon(rk)
            if bh is None:
                st.warning(
                    "Inget tidsfönster (1 vecka–9 månader) visar ännu en tillförlitlig "
                    "avvikelse från basnivån för det här mönstret — obevisat, inte bekräftat "
                    "obrukbart. Se grafen nedan för hela bilden.",
                    icon="🚫",
                )
            else:
                mult = bh["lift"]
                comp = (
                    f"ungefär {mult:.1f} gånger så ofta som normalt ({bh['base_rate']:.0%})" if mult >= 1.25
                    else f"ungefär lika ofta som normalt ({bh['base_rate']:.0%})"
                )
                st.markdown(
                    f"När mönstret lyst har en uppgång på **minst +50 % inom {bh['label']}** "
                    f"— det kortaste fönster där mönstret visar en tillförlitlig avvikelse — "
                    f"följt i **{bh['hit_rate']:.0%}** av fallen — {comp}."
                )
                if bh.get("med_max_ret") is not None:
                    st.markdown(
                        f"Största rörelse inom samma period (median i historiken): "
                        f"upp **{bh['med_max_ret']:+.0%}**, ned **{bh['med_max_dd']:+.0%}**."
                    )

            with st.expander("Visa alla tidsfönster (graf)"):
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

# --------------------------------------------------------- loggen
st.divider()
with st.expander("Signalloggen (senaste 100)"):
    lg = recent_signal_log(100)
    if lg.empty:
        st.write("Tom.")
    else:
        lg = lg.copy()
        lg["Signal utfärdad"] = pd.to_datetime(lg["as_of_date"]).dt.strftime("%Y-%m-%d")
        lg["Mönster"] = lg["rule"].map({k: v["titel"] for k, v in RULE_SV.items()}).fillna(lg["rule"])
        lg = lg.rename(columns={"name": "Bolag"})
        st.dataframe(lg[["Signal utfärdad", "Bolag", "Mönster"]], hide_index=True, width="stretch")
