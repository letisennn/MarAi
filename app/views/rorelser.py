"""Rörelser & utbrott — de största kursrörelserna just nu, och vad som syntes
i mätvärdena veckorna innan. Svarar på "fanns det en signal i förväg?".
Beskrivande historik, ingen prognos."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _data import (
    historical_breakouts,
    move_precursor,
    movers,
    verdict,
)

st.title("Rörelser & utbrott")
st.caption(
    "De största kursrörelserna i universumet, störst först. För varje bolag: vad "
    "mätvärdena visade veckorna innan. Om inget syntes i förväg står det så — det är "
    "också ett resultat. Data: Yahoo Finance. Syntetisk attention-data."
)

c1, c2 = st.columns(2)
win_label = c1.radio(
    "Fönster", ["1 vecka", "1 månad", "3 månader", "12 månader"], index=1, horizontal=True
)
seg_label = c2.radio("Urval", ["Bara small", "Alla i universumet"], index=0, horizontal=True)
win = {"1 vecka": "1w", "1 månad": "1m", "3 månader": "3m", "12 månader": "12m"}[win_label]
seg = "small" if seg_label == "Bara small" else "alla"

mv = movers(window=win, segment=seg, limit=30)
if mv.empty:
    st.info("Inga rörelser att visa.")
    st.stop()

# --- panelbred kontext: syntes något innan historiska utbrott? --------------
hb = historical_breakouts(0.25)
if hb.get("n"):
    n = int(hb["n"])
    pv = hb.get("p_high_vol") or 0.0
    pr = hb.get("p_vol_rising") or 0.0
    pnh = hb.get("p_near_high") or 0.0
    pall = hb.get("p_high_vol_all")
    extra = f" (mot {pall:.0%} av alla veckor)" if pall is not None else ""
    st.markdown(
        f"**Historiskt, small-segmentet:** av **{n}** veckor som följdes av minst "
        f"**+25 % på 20 dagar** hade **{pv:.0%}** förhöjd volym redan samma vecka{extra}, "
        f"**{pr:.0%}** stigande handel och **{pnh:.0%}** låg nära årshögsta. "
        "Så *ibland* syns något i förväg — men långt ifrån alltid."
    )
st.divider()

# --- tabell över nuvarande rörelser ---------------------------------------
def _pp(v):  # andel -> procentenheter, None-säkert
    return round(v * 100, 0) if v is not None and pd.notna(v) else None


rows = []
for _, r in mv.iterrows():
    vd = verdict(int(r["security_id"]))
    rows.append({
        "Bolag": r["name"],
        f"Rörelse {win_label}": _pp(r["move"]),
        "Marc-läge": f"{vd['ikon']} {vd['kategori']}",
        "Från årshögsta": _pp(r["dist_52w_high"]),
        "Volym mot normalt": _pp(r["rvol_5_60"] - 1.0) if pd.notna(r["rvol_5_60"]) else None,
        "Sektor": r["sector"],
        "Segment": r["segment"],
    })
st.dataframe(
    pd.DataFrame(rows),
    hide_index=True,
    width="stretch",
    column_config={
        f"Rörelse {win_label}": st.column_config.NumberColumn(format="%+.0f%%", help="Kursutveckling över fönstret"),
        "Från årshögsta": st.column_config.NumberColumn(format="%+.0f%%"),
        "Volym mot normalt": st.column_config.NumberColumn(format="%+.0f%%", help="0 % = normal handel"),
    },
)

st.divider()

# --- ett bolag: vad syntes veckorna innan -------------------------------------
st.subheader("Vad syntes i förväg?")
pick = st.selectbox("Välj ett bolag ur listan", mv["name"].tolist())
sid = int(mv.loc[mv["name"] == pick, "security_id"].iloc[0])

vd = verdict(sid)
st.markdown(f"**{pick}** — läge nu: {vd['ikon']} **{vd['kategori']}**. {vd['slutsats']}")

pc = move_precursor(sid, weeks_before=5)
if pc.empty:
    st.info("Ingen veckohistorik för det här bolaget.")
else:
    disp = pd.DataFrame({"Vecka": pd.to_datetime(pc["obs_date"]).dt.strftime("%Y-%m-%d")})
    if "ret_1w" in pc:
        disp["Kurs 1 vecka"] = (pc["ret_1w"] * 100).round(0)
    if "rvol_5_60" in pc:
        disp["Volym mot normalt"] = ((pc["rvol_5_60"] - 1.0) * 100).round(0)
    if "vol_accel" in pc:
        disp["Handeln"] = pc["vol_accel"].map(
            lambda v: "stiger" if pd.notna(v) and v > 0 else ("faller" if pd.notna(v) and v < 0 else "–")
        )
    if "dist_52w_high" in pc:
        disp["Från årshögsta"] = (pc["dist_52w_high"] * 100).round(0)
    if "search_accel" in pc:
        disp["Sökintresse"] = pc["search_accel"].map(
            lambda v: "ökar" if pd.notna(v) and v > 0.1 else ("minskar" if pd.notna(v) and v < -0.1 else "–")
        )
    disp["Mönster lyste"] = pc["monster_lyste"]
    st.dataframe(
        disp, hide_index=True, width="stretch",
        column_config={
            "Kurs 1 vecka": st.column_config.NumberColumn(format="%+.0f%%"),
            "Volym mot normalt": st.column_config.NumberColumn(format="%+.0f%%"),
            "Från årshögsta": st.column_config.NumberColumn(format="%+.0f%%"),
        },
    )

    # plain-language läsning av raderna före den sista
    before = pc.iloc[:-1]
    hint_vol = "rvol_5_60" in before and (before["rvol_5_60"] > 1.3).any()
    hint_acc = "vol_accel" in before and (before["vol_accel"] > 0).any()
    hint_pat = (before["monster_lyste"] != "—").any() if "monster_lyste" in before else False
    if hint_pat:
        st.success("Minst ett förregistrerat mönster lyste i veckorna innan.")
    elif hint_vol or hint_acc:
        st.info(
            "Inget förregistrerat mönster lyste, men handeln var förhöjd eller stigande "
            "redan veckorna innan — ett svagare förvarningstecken."
        )
    else:
        st.warning(
            "Inget syntes i mätvärdena veckorna innan — rörelsen kom utan förvarning i datan. "
            "Det är den vanligaste utgången, och därför signalerna ännu inte är bevisade."
        )

st.caption(
    "Allt ovan är beskrivande historik. Inget här är en validerad prediktiv signal — "
    "det kräver test mot en kontrollgrupp på data som inte användes för att hitta mönstret."
)
