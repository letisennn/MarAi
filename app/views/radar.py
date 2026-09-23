"""Market Radar — vilka bolag håller på att gå från låg till accelererande
marknadsintresse, INNAN det syns för alla. Rankas i första hand på
Uppbyggnadspoäng, inte på hur mycket ett bolag redan gått."""

from __future__ import annotations

import streamlit as st

from _data import (
    PHASE_SV,
    data_source,
    latest_obs_date,
    market_radar,
    radar_sparklines,
    security_list,
)
from _guide import radar_guide

st.title("📡 Market Radar")
d = latest_obs_date()
src = "syntetisk data" if data_source() == "synthetic" else "Yahoo Finance"
st.caption(
    f"Bolag i universumet, senaste datavecka {d:%Y-%m-%d} · källa: {src}. Sorterat på "
    "**Bedömning** — Noels färdiga tolkning, inte ett tal du behöver läsa själv."
)
radar_guide()

# --------------------------------------------------------------- kontroller
c1, c2, c3 = st.columns([2, 3, 3])
seg = c1.radio("Urval", ["Bara small", "Alla"], horizontal=True)
segment = "small" if seg == "Bara small" else "alla"
hide_visible = c2.checkbox("Dölj bolag som redan är \"synliga för alla\"", value=True)
show_advanced = c3.toggle(
    "Visa alla mått (avancerat)",
    value=False,
    help="Rådata bakom Bedömning: Discovery-referens, attention, momentum, mönster.",
)

radar = market_radar(segment=segment)
if radar.empty:
    st.warning("Ingen radardata — är pipelinen körd?")
    st.stop()


def _open_company(name: str) -> None:
    st.session_state["sel_security"] = name
    st.session_state["_bolag_opened"] = True
    st.switch_page("views/bolag_detalj.py")


# Två vägar in i ett bolag, båda direkt (ingen extra knapp att hitta): sök/välj
# här, eller klicka en rad i tabellen nedan. Väljaren söker bland ALLA bolag i
# databasen — även de som fallit ur radarns universum (t.ex. Climeon) och de
# som filtren nedan råkar dölja.
open_pick = st.selectbox(
    "📂 Öppna ett bolag direkt",
    security_list()["name"].dropna().tolist(),
    index=None,
    placeholder="Sök eller välj bolag för full analys…",
    key="radar_open_pick",
)
if open_pick:
    _open_company(str(open_pick))

f1, f2, f3 = st.columns([3, 2, 2])
txt = f1.text_input("🔎 Sök bolagsnamn")
sectors = sorted(radar["Sektor"].dropna().unique())
pick_sector = f2.multiselect("Sektor", sectors)
countries = sorted(radar["Land"].dropna().unique())
pick_country = f3.multiselect("Land", countries)

if hide_visible:
    radar = radar[~radar["Redan synligt"].fillna(False)]
if txt:
    radar = radar[radar["Bolag"].str.contains(txt, case=False, na=False)]
if pick_sector:
    radar = radar[radar["Sektor"].isin(pick_sector)]
if pick_country:
    radar = radar[radar["Land"].isin(pick_country)]
radar = radar.sort_values("Uppbyggnad", ascending=False, na_position="last").reset_index(drop=True)

if radar.empty:
    st.warning("Inga bolag matchar filtren.")
    st.stop()

# --------------------------------------------------------------- pulsremsa
_BAND_EMOJI = {
    "Inget setup": "⚪", "Bevaka": "🔎", "Tidigt setup": "🌱",
    "Starkt setup": "📈", "Mycket starkt setup": "🔥",
}
_BAND_ORDER = ["Mycket starkt setup", "Starkt setup", "Tidigt setup", "Bevaka", "Inget setup"]

band_counts = radar["Uppbyggnadsband"].value_counts()
n_visible_hidden = int(radar["Redan synligt"].fillna(False).sum()) if not hide_visible else None
pulse_cols = st.columns(len(_BAND_ORDER) + (0 if hide_visible else 1))
for col, band in zip(pulse_cols, _BAND_ORDER, strict=False):
    col.metric(f"{_BAND_EMOJI[band]} {band}", int(band_counts.get(band, 0)))
if not hide_visible:
    pulse_cols[-1].metric("⚠️ Redan synligt", n_visible_hidden or 0)

st.divider()


def _bedomning(band, visible) -> str:
    if bool(visible):
        return "⚠️ Redan synligt"
    b = band if isinstance(band, str) else "–"
    return f"{_BAND_EMOJI.get(b, '')} {b}".strip()


# --------------------------------------------------------------- sparklines
spark = radar_sparklines(days=90)
show = radar[["Bolag", "Uppbyggnad", "Fas", "Sektor", "Land"]].copy()
show.insert(1, "Bedömning", [
    _bedomning(b, v) for b, v in zip(radar["Uppbyggnadsband"], radar["Redan synligt"], strict=False)
])
show.insert(3, "Kurs (90d)", [spark.get(sid, {}).get("kurs", []) for sid in radar["security_id"]])
show.insert(4, "Volym (90d)", [spark.get(sid, {}).get("volym", []) for sid in radar["security_id"]])
if show_advanced:
    for c in ["Discovery", "Attention-accel", "Volym mot normalt", "Kurs 1 mån", "Kurs 3 mån", "Från årshögsta"]:
        show[c] = radar[c] * 100 if c != "Discovery" else radar[c]
    show["Mönster"] = radar["Mönster"]

st.caption(f"{len(show)} bolag i listan. 👆 **Klicka på en rad för att öppna bolagets fulla analys.**")
sel = st.dataframe(
    show,
    hide_index=True,
    width="stretch",
    height=560,
    on_select="rerun",
    selection_mode="single-row",
    key="radar_table",
    column_config={
        "Bedömning": st.column_config.TextColumn(
            help="Uppbyggnadspoängets band, eller att bolaget redan syns för alla.",
        ),
        "Uppbyggnad": st.column_config.ProgressColumn(
            "Uppbyggnad", min_value=0, max_value=100, format="%.0f",
            help="Letar läget FÖRE en rörelse — huvudrankningen. Experimentell, ovaliderad.",
        ),
        "Kurs (90d)": st.column_config.LineChartColumn(
            "Kurs (90d)", help="Kursens form senaste ~90 handelsdagarna — lugn eller redan i rörelse?",
        ),
        "Volym (90d)": st.column_config.BarChartColumn(
            "Volym (90d)", help="Omsatt belopp (SEK) per dag senaste ~90 handelsdagarna — bygger handeln på?",
        ),
        "Discovery": st.column_config.ProgressColumn(
            "Discovery (ref.)", min_value=0, max_value=100, format="%.0f",
            help="Hur starkt bolaget rör sig just nu — inte samma sak som tidigt läge.",
        ),
        "Attention-accel": st.column_config.NumberColumn("Attention ↑", format="%+.0f%%",
                                                         help="Sökacceleration (syntetisk data)"),
        "Volym mot normalt": st.column_config.NumberColumn("Volym", format="%+.0f%%",
                                                           help="0 % = normal handel"),
        "Kurs 1 mån": st.column_config.NumberColumn("Kurs 1m", format="%+.0f%%"),
        "Kurs 3 mån": st.column_config.NumberColumn("Kurs 3m", format="%+.0f%%"),
        "Från årshögsta": st.column_config.NumberColumn("Från ÅH", format="%+.0f%%"),
        "Mönster": st.column_config.NumberColumn("Mönster", format="%d",
                                                help="Antal förregistrerade mönster som lyst senaste veckorna"),
    },
)

rows = sel.get("selection", {}).get("rows", []) if isinstance(sel, dict) else []
if rows:
    _open_company(str(radar.iloc[rows[0]]["Bolag"]))

with st.expander("Vad betyder faserna?"):
    st.markdown(
        "\n".join(
            f"- **{PHASE_SV[k]}** — {n}"
            for k, n in {
                "low": "normal/låg handel, inget ökande intresse",
                "early": "handel eller sökintresse börjar ticka upp från låg nivå, kursen har inte dragit",
                "accelerating": "uppmärksamhet och volym ökar i takt, kursen rör sig uppåt",
                "hype": "hög och stigande uppmärksamhet, kraftig volym, stark kursrörelse",
                "mass": "uppmärksamheten hög men ökar inte längre, kursen utsträckt",
                "exhaustion": "uppmärksamheten faller tillbaka medan kursen vänder ner",
                "reversal": "fallande intresse och kurs, en bit under årshögsta",
            }.items()
        )
    )
    st.caption(
        "Fasmodellen är beskrivande. Ingen fas betyder automatiskt köp eller sälj — "
        "om faserna bär information ska det visas historiskt (Signal Lab / Forskning)."
    )
