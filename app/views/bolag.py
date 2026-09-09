"""Bolag — alla bolag i en sökbar, sorterbar tabell. Klick öppnar bolaget i detalj."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _data import all_scores, latest_obs_date, screener

st.title("📋 Alla bolag")

d = latest_obs_date()
st.caption(
    f"Alla bolag i databasen, med de senaste mätningarna (panelen slutar {d:%Y-%m-%d}). "
    "**Klicka på en rad för att öppna hela genomgången.** \"Discovery Score\" är en "
    "**preliminär** poäng med ovaliderade vikter. Segment: *small* = genuina småbolag "
    "(huvudfokus), *mid* = har vuxit förbi taket men behålls. Klicka på en kolumnrubrik "
    "för att sortera."
)

weeks = st.slider(
    "\"Mönster som lyst\"-kolumnen räknar de senaste … veckorna",
    min_value=1, max_value=26, value=8,
)
df = screener(weeks=weeks)

seg = st.radio(
    "Segment",
    ["Bara small (småbolag – huvudfokus)", "Small + mid", "Alla bolag i databasen"],
    horizontal=True,
)

f1, f2, f3 = st.columns([2, 2, 3])
countries = sorted(df["country"].dropna().unique())
sectors = sorted(df["sector"].dropna().unique())
pick_c = f1.multiselect("Land", countries)
pick_s = f2.multiselect("Sektor", sectors)
txt = f3.text_input("Sök bolagsnamn")

o1, o2 = st.columns(2)
only_uni = o1.checkbox("Bara bolag i universum senaste veckan")
only_sig = o2.checkbox(f"Bara bolag med mönster som lyst senaste {weeks} veckorna")

view = df.copy()
if seg.startswith("Bara small"):
    view = view[view["segment"] == "small"]
elif seg.startswith("Small + mid"):
    view = view[view["segment"].isin(["small", "mid"])]
if pick_c:
    view = view[view["country"].isin(pick_c)]
if pick_s:
    view = view[view["sector"].isin(pick_s)]
if txt:
    view = view[view["name"].str.contains(txt, case=False, na=False)]
if only_uni:
    view = view[view["in_universe_now"]]
if only_sig:
    view = view[view["n_rules"] > 0]

sc = all_scores(weeks=weeks)
view = view.merge(sc, on="security_id", how="left").sort_values(
    "score", ascending=False, na_position="last"
)

# handel som procent mot normalt: 1.8 -> "+80 %", 0.6 -> "-40 %"
handel_pct = ((view["rvol_5_60"] - 1.0) * 100)

show = pd.DataFrame(
    {
        "Bolag": view["name"].values,
        "Discovery": view["score"].values,
        "Bedömning": view["band"].fillna("–").values,
        "Sektor": view["sector"].values,
        "Land": view["country"].values,
        "Börsvärde (MSEK)": (view["market_cap_sek"] / 1e6).values,
        "Segment": view["segment"].fillna("—").values,
        "Status": view["status_sv"].values,
        "Kurs 3 mån (%)": (view["ret_3m"] * 100).values,
        "Kurs 1 år (%)": (view["ret_12m"] * 100).values,
        "Handel mot normalt (%)": handel_pct.values,
        "Från årshögsta (%)": (view["dist_52w_high"] * 100).values,
        "Mönster som lyst": view["n_rules"].astype(int).values,
        "Senaste signal": pd.to_datetime(view["last_signal"]).values,
    }
)

st.caption(f"{len(show)} bolag.")
event = st.dataframe(
    show,
    hide_index=True,
    width="stretch",
    height=560,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Discovery": st.column_config.ProgressColumn(
            format="%.0f", min_value=0, max_value=100,
            help="Experimentell, ovaliderad poäng 0–100 — momentum, läge mot årshögsta, handel, mönster",
        ),
        "Börsvärde (MSEK)": st.column_config.NumberColumn(format="%.0f"),
        "Kurs 3 mån (%)": st.column_config.NumberColumn(
            format="%+.0f", help="Kursförändring senaste 3 månaderna, i procentenheter"
        ),
        "Kurs 1 år (%)": st.column_config.NumberColumn(format="%+.0f"),
        "Handel mot normalt (%)": st.column_config.NumberColumn(
            format="%+.0f", help="+80 = 80 % mer handel än normalt, -40 = 40 % mindre"
        ),
        "Från årshögsta (%)": st.column_config.NumberColumn(
            format="%+.0f", help="0 = vid årshögsta, -20 = tjugo procent under"
        ),
        "Mönster som lyst": st.column_config.NumberColumn(
            help=f"Antal förregistrerade mönster som lyst de senaste {weeks} veckorna"
        ),
        "Senaste signal": st.column_config.DateColumn(format="YYYY-MM-DD"),
    },
)

rows: list[int] = []
try:
    rows = list(event.selection["rows"])
except (KeyError, TypeError, AttributeError):
    rows = []

if rows:
    name = str(show.iloc[rows[0]]["Bolag"])
    if st.session_state.get("_bolag_opened") != name:
        st.session_state["_bolag_opened"] = name
        st.session_state["sel_security"] = name
        st.switch_page("views/bolag_detalj.py")
    st.page_link("views/bolag_detalj.py", label=f"→ Öppna {name} i detalj", icon="🔎")
