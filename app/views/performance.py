"""Performance — uppföljning av sparade upptäckter (paper trading).

Datamodellen finns (``discovery`` + ``discovery_outcome``). Automatisk
tracking är inte påkopplad än; den här vyn visar vad som finns och hur det
kommer att se ut."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _data import discovery_log, discovery_performance

st.title("📊 Noel Performance")
st.caption(
    "Följer upp varje sparad 'discovery' mot vad aktien faktiskt gjorde "
    "(+1 / +5 / +20 / +30 / +60 / +90 dagar), jämfört med kontroll/benchmark."
)

perf = discovery_performance()
log = discovery_log()

if perf.get("n", 0) == 0:
    st.info(
        "**Inga upptäckter registrerade än.**\n\n"
        "Datamodellen är på plats: en upptäckt sparas med tidsstämpel, kurs, "
        "discovery-score, fas, feature-snapshot, motivering och analog-statistik "
        "vid tillfället. När horisonterna passerat fylls utfallet i automatiskt "
        "och den här sidan visar snitt-/medianavkastning, träffkvot, andel som "
        "nådde +25 %/30 d och +50 %/90 d, mot en kontrollgrupp.",
        icon="🗂️",
    )
    st.subheader("Så här kommer tabellen att se ut")
    demo = pd.DataFrame(
        {
            "Horisont": ["+1 d", "+5 d", "+20 d", "+30 d", "+60 d", "+90 d"],
            "Antal": ["—"] * 6,
            "Median-avk.": ["—"] * 6,
            "Snitt-avk.": ["—"] * 6,
            "Träffkvot": ["—"] * 6,
        }
    )
    st.dataframe(demo, hide_index=True, width="stretch")
    st.stop()

st.metric("Registrerade upptäckter", perf["n"])
by_h = perf.get("by_horizon")
if by_h is not None and not by_h.empty:
    disp = by_h.rename(columns={
        "horizon": "Horisont", "n": "Antal", "mean_ret": "Snitt-avk.",
        "median_ret": "Median-avk.", "win_rate": "Träffkvot",
    })
    for c in ["Snitt-avk.", "Median-avk.", "Träffkvot"]:
        if c in disp:
            disp[c] = (disp[c] * 100).round(1)
    st.dataframe(disp, hide_index=True, width="stretch",
                 column_config={
                     "Snitt-avk.": st.column_config.NumberColumn(format="%+.1f%%"),
                     "Median-avk.": st.column_config.NumberColumn(format="%+.1f%%"),
                     "Träffkvot": st.column_config.NumberColumn(format="%.0f%%"),
                 })
else:
    st.caption("Upptäckter finns men inga utfall utvärderade än.")

st.subheader("Logg")
st.dataframe(
    log.rename(columns={
        "as_of_date": "Datum", "bolag": "Bolag", "source": "Källa",
        "discovery_score": "Score", "phase_key": "Fas", "entry_price_sek": "Kurs",
        "reason": "Motivering",
    }),
    hide_index=True,
    width="stretch",
)
