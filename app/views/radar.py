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
)

st.title("📡 Market Radar")
d = latest_obs_date()
src = "syntetisk data" if data_source() == "synthetic" else "Yahoo Finance"
st.caption(f"Bolag i universumet, senaste datavecka {d:%Y-%m-%d} · källa: {src}.")
st.info(
    "**Uppbyggnadspoäng** letar bolag INNAN de syns: tyst kurs + stigande volym/"
    "uppmärksamhet, en bit under (inte vid) årshögsta. Bolag redan nära årshögsta "
    "med stor uppgång bakom sig ger inget informationsövertag — vem som helst kan "
    "se det — och rankas därför lågt här (se dem i stället under Rörelser & "
    "utbrott). **Discovery Score** visas som referens: den mäter hur starkt ett "
    "bolag rör sig *just nu*, inte hur tidigt läget är. Båda är experimentella, "
    "ovaliderade.",
    icon="🧪",
)

c1, c2, c3 = st.columns([2, 2, 3])
seg = c1.radio("Urval", ["Bara small", "Alla"], horizontal=True)
segment = "small" if seg == "Bara small" else "alla"
sort_by = c2.selectbox(
    "Sortera på",
    ["Uppbyggnadspoäng", "Discovery Score (referens)", "Attention-acceleration",
     "Volym mot normalt", "Kursmomentum 1 mån", "Fas (längst i cykeln först)"],
)
hide_visible = c3.checkbox("Dölj bolag som redan är \"synliga för alla\"", value=True)

radar = market_radar(segment=segment)
if radar.empty:
    st.warning("Ingen radardata — är pipelinen körd?")
    st.stop()

if hide_visible:
    radar = radar[~radar["Redan synligt"].fillna(False)]

sort_col = {
    "Uppbyggnadspoäng": ("Uppbyggnad", False),
    "Discovery Score (referens)": ("Discovery", False),
    "Attention-acceleration": ("Attention-accel", False),
    "Volym mot normalt": ("Volym mot normalt", False),
    "Kursmomentum 1 mån": ("Kurs 1 mån", False),
    "Fas (längst i cykeln först)": ("phase_idx", False),
}[sort_by]
radar = radar.sort_values(sort_col[0], ascending=sort_col[1], na_position="last").reset_index(drop=True)

show = radar[[
    "Bolag", "Uppbyggnad", "Discovery", "Fas", "Attention-accel", "Volym mot normalt",
    "Kurs 1 mån", "Kurs 3 mån", "Från årshögsta", "Mönster", "Sektor",
]].copy()
show["Redan synligt"] = radar["Redan synligt"].map({True: "⚠️ Ja", False: ""}).fillna("")
for c in ["Attention-accel", "Volym mot normalt", "Kurs 1 mån", "Kurs 3 mån", "Från årshögsta"]:
    show[c] = show[c] * 100

sel = st.dataframe(
    show,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Uppbyggnad": st.column_config.ProgressColumn(
            "Uppbyggnad", min_value=0, max_value=100, format="%.0f",
            help="Letar läget FÖRE en rörelse — huvudrankningen. Experimentell, ovaliderad.",
        ),
        "Discovery": st.column_config.ProgressColumn(
            "Discovery (ref.)", min_value=0, max_value=100, format="%.0f",
            help="Hur starkt bolaget rör sig just nu — inte samma sak som tidigt läge.",
        ),
        "Redan synligt": st.column_config.TextColumn(
            "⚠️", help="Redan nära årshögsta med stor uppgång bakom sig — inget övertag att peka på det.",
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
    pick = str(radar.iloc[rows[0]]["Bolag"])
    st.session_state["sel_security"] = pick
    st.session_state["_bolag_opened"] = True
    st.switch_page("views/bolag_detalj.py")

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
