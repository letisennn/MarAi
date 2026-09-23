"""Bolag — alla bolag i en sökbar, sorterbar tabell. Klick öppnar bolaget i detalj."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _data import all_scores, all_setup_scores, latest_obs_date, screener
from _guide import alla_bolag_guide

st.title("📋 Alla bolag")
alla_bolag_guide()

d = latest_obs_date()
st.caption(
    f"Alla bolag i databasen, senast mätt {d:%Y-%m-%d}. **Klicka på en rad för att öppna "
    "hela genomgången.** Sorterat på **Bedömning** — Noels färdiga tolkning av läget, "
    "inte bara ett högt eller lågt tal. Klicka en kolumnrubrik för att sortera om."
)

weeks = 8
show_advanced = st.toggle(
    "Visa alla mått (avancerat)",
    help="Rådata bakom Bedömning: Discovery-referens, kursutveckling, handel, "
    "mönsterträffar. Av som standard — Bedömning-kolumnen sammanfattar redan det viktiga.",
)
if show_advanced:
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
su = all_setup_scores()
view = (
    view.merge(sc, on="security_id", how="left")
    .merge(su, on="security_id", how="left")
    .sort_values("setup_score", ascending=False, na_position="last")
)

# handel som procent mot normalt: 1.8 -> "+80 %", 0.6 -> "-40 %"
handel_pct = ((view["rvol_5_60"] - 1.0) * 100)

_BAND_EMOJI = {
    "Inget setup": "⚪", "Bevaka": "🔎", "Tidigt setup": "🌱",
    "Starkt setup": "📈", "Mycket starkt setup": "🔥",
}


def _bedomning(band, visible) -> str:
    if bool(visible):
        return "⚠️ Redan synligt"
    b = band if isinstance(band, str) else "–"
    return f"{_BAND_EMOJI.get(b, '')} {b}".strip()


show = pd.DataFrame(
    {
        "Bolag": view["name"].values,
        "Bedömning": [
            _bedomning(b, v) for b, v in zip(view["setup_band"], view["already_visible"], strict=False)
        ],
        "Uppbyggnad": view["setup_score"].values,
        "Sektor": view["sector"].values,
        "Land": view["country"].values,
        "Börsvärde (MSEK)": (view["market_cap_sek"] / 1e6).values,
        "Senaste signal": pd.to_datetime(view["last_signal"]).values,
        "Discovery (referens)": view["score"].values,
        "Segment": view["segment"].fillna("—").values,
        "Status": view["status_sv"].values,
        "Kurs 3 mån (%)": (view["ret_3m"] * 100).values,
        "Kurs 1 år (%)": (view["ret_12m"] * 100).values,
        "Handel mot normalt (%)": handel_pct.values,
        "Från årshögsta (%)": (view["dist_52w_high"] * 100).values,
        "Mönster som lyst": view["n_rules"].astype(int).values,
    }
)

base_cols = ["Bolag", "Bedömning", "Uppbyggnad", "Sektor", "Land", "Börsvärde (MSEK)", "Senaste signal"]
adv_cols = ["Discovery (referens)", "Segment", "Status", "Kurs 3 mån (%)", "Kurs 1 år (%)",
            "Handel mot normalt (%)", "Från årshögsta (%)", "Mönster som lyst"]
cols = base_cols + adv_cols if show_advanced else base_cols

st.caption(f"{len(show)} bolag.")
event = st.dataframe(
    show[cols],
    hide_index=True,
    width="stretch",
    height=560,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Bedömning": st.column_config.TextColumn(
            help="Noels färdiga tolkning: Uppbyggnadspoängets band, eller att bolaget redan "
                 "är synligt för alla (nära årshögsta, stor uppgång bakom sig — inget övertag).",
        ),
        "Uppbyggnad": st.column_config.ProgressColumn(
            format="%.0f", min_value=0, max_value=100,
            help="Letar läget FÖRE en rörelse — huvudrankning. Experimentell, ovaliderad.",
        ),
        "Börsvärde (MSEK)": st.column_config.NumberColumn(format="%.0f"),
        "Senaste signal": st.column_config.DateColumn(
            format="YYYY-MM-DD",
            help="Datum ett förregistrerat mönster senast lyste. Tidshorisont varierar per "
                 "mönster (inte samma tal för alla) — se Bolag i detalj.",
        ),
        "Discovery (referens)": st.column_config.ProgressColumn(
            format="%.0f", min_value=0, max_value=100,
            help="Hur starkt bolaget rör sig JUST NU (referens) — momentum, läge mot årshögsta, handel, mönster. "
                 "Experimentell, ovaliderad.",
        ),
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
