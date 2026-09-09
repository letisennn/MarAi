"""Dagens upptäckter — de kandidater radarn lyfter fram just nu, med en
klarspråksförklaring och historiska analoger. Experimentell rankning."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _data import (
    analogues,
    daily_discoveries,
    latest_obs_date,
    security_list,
    verdict,
)

st.title("🌅 Dagens upptäckter")
d = latest_obs_date()
st.caption(f"Senaste datavecka {d:%Y-%m-%d}. Kandidaterna väljs på experimentell "
           "Discovery Score bland bolag i en tidig/accelererande fas.")
st.info(
    "**Experimentell discovery-rankning** — Discovery Score är inte statistiskt "
    "validerad. Det här är lägen att undersöka, inte rekommendationer.",
    icon="🧪",
)

seg = st.radio("Urval", ["Bara small", "Alla"], horizontal=True)
picks = daily_discoveries(n=8, segment="small" if seg == "Bara small" else "alla")
if picks.empty:
    st.warning("Inga kandidater i en tidig/accelererande fas just nu.")
    st.stop()

names = security_list().set_index("name")["security_id"].to_dict()
medal = {0: "🥇", 1: "🥈", 2: "🥉"}

for i, row in picks.iterrows():
    nm = str(row["Bolag"])
    sid = int(names.get(nm))
    vd = verdict(sid)
    with st.container(border=True):
        head = f"{medal.get(i, f'#{i + 1}')} **{nm}**"
        sc = row["Discovery"]
        st.markdown(f"### {head}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Discovery (exp.)", f"{sc:.0f}/100" if pd.notna(sc) else "—")
        m2.metric("Fas", row["Fas"])
        mv = row["Volym mot normalt"]
        m3.metric("Volym mot normalt", f"{mv * 100:+.0f}%" if pd.notna(mv) else "—")

        st.markdown(f"**Varför är detta intressant?** {vd['slutsats']}")
        if vd["darfor"]:
            st.markdown("\n".join(f"- {x}" for x in vd["darfor"][:3]))

        a = analogues(sid, k=40)
        if a.get("n_analogues", 0) >= 10:
            h30 = a["horizons"].get(30, {})
            h90 = a["horizons"].get(90, {})
            r50 = a.get("reached_50_within_90d")
            line = f"**{a['n_analogues']} historiska analoger** ({a['n_distinct_names']} olika bolag). "
            if h30.get("median_ret") is not None:
                line += f"Median +30 d: {h30['median_ret'] * 100:+.1f} %. "
            if h90.get("median_ret") is not None:
                line += f"Median +90 d: {h90['median_ret'] * 100:+.1f} %. "
            if r50:
                line += f"Nådde +50 % inom 90 d: {r50[0]}/{r50[1]}."
            st.markdown(line)
            if h90.get("lift") is not None:
                lift = h90["lift"]
                verdict_txt = (
                    "över kontrollgruppen" if lift >= 1.15
                    else "under kontrollgruppen" if lift <= 0.85
                    else "i linje med kontrollgruppen"
                )
                st.caption(f"Träffgrad +50 %/90 d är {verdict_txt} (lift {lift:.2f}). "
                           "Litet urval — preliminärt, ej säkerställt.")
        else:
            st.caption("För få historiska analoger för tillförlitlig statistik.")

        if st.button("Öppna full analys", key=f"open_{sid}"):
            st.session_state["sel_security"] = nm
            st.session_state["_bolag_opened"] = True
            st.switch_page("views/bolag_detalj.py")

st.caption(
    "Datamodellen stödjer paper trading: varje kandidat kan sparas som en "
    "'discovery' och följas upp automatiskt (+1/5/20/30/60/90 d). Se Performance."
)
