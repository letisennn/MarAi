"""Översikt — startsidan. Leder med en färdig slutsats (dagens bästa kandidat +
portföljläget), inte en spreadsheet. Allt tekniskt/bakgrund ligger i expanders
längst ner för den som vill gräva."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import _paper
from _data import (
    EVENT_CODE_SV,
    base_rates,
    daily_discoveries,
    data_source,
    kpis,
    latest_prices_all,
    pipeline_status,
    security_list,
    verdict,
)
from _guide import overview_guide
from _style import big_number, pnl_color

st.title("📡 Noel AI")

if data_source() == "synthetic":
    st.warning(
        "**Syntetisk data.** Siffrorna i appen är exempel på utdataform, inte "
        "marknadsresultat, tills en riktig priskälla kopplats in."
    )

overview_guide()

# =============================================================== dagens bästa kandidat
st.subheader("🌅 Bästa kandidaten just nu")
picks = daily_discoveries(n=1, segment="small")
if picks.empty:
    st.info("Inga kandidater i en tidig/accelererande fas just nu.")
else:
    names = security_list().set_index("name")["security_id"].to_dict()
    row = picks.iloc[0]
    nm = str(row["Bolag"])
    sid = int(names.get(nm))
    vd = verdict(sid)
    with st.container(border=True):
        st.markdown(f"### {vd['ikon']} {nm} — {vd['kategori']}")
        meta_bits = []
        if vd.get("as_of") is not None:
            meta_bits.append(f"📅 Utfärdad {pd.Timestamp(vd['as_of']):%Y-%m-%d}")
        if vd.get("horisont"):
            meta_bits.append(f"⏱ Tidshorisont {vd['horisont']}")
        if meta_bits:
            st.caption("  ·  ".join(meta_bits))
        st.markdown(f"**{vd['slutsats']}**")
        if vd["darfor"]:
            st.markdown("\n".join(f"- {x}" for x in vd["darfor"][:3]))
        b1, b2 = st.columns(2)
        if b1.button("Öppna full analys", key="start_open"):
            st.session_state["sel_security"] = nm
            st.session_state["_bolag_opened"] = True
            st.switch_page("views/bolag_detalj.py")
        if b2.button("🌅 Fler kandidater", key="start_more"):
            st.switch_page("views/dagens.py")

st.divider()

# =============================================================== portfölj
owner = st.session_state.get("paper_owner", _paper.DEFAULT_OWNER)
st.subheader(f"💼 {owner.capitalize()}s portfölj (paperhandel)")
prices = latest_prices_all()
acct = _paper.summary(owner, prices)
p1, p2, p3, p4 = st.columns(4)
p1.metric("Totalt värde", f"{acct['total_value']:,.0f} kr".replace(",", " "))
p2.metric("Kassa", f"{acct['cash']:,.0f} kr".replace(",", " "))
with p3:
    big_number("Totalt resultat", f"{acct['total_pnl']:+,.0f} kr".replace(",", " "), pnl_color(acct["total_pnl"]),
                sub=None if acct["total_pnl_pct"] is None else f"{acct['total_pnl_pct'] * 100:+.1f} %")
if p4.button("Öppna paperhandel →"):
    st.switch_page("views/portfolio.py")
if acct["n_trades"] == 0:
    st.caption(f"Inga affärer än. Startkapital: {acct['starting_capital']:,.0f} kr.".replace(",", " "))

st.divider()

# =============================================================== snabblänkar
st.subheader("Vart tar jag vägen?")
a, b, c = st.columns(3)
with a:
    st.markdown("#### 📡 Market Radar")
    st.write("Alla bolag rankade på hur tidigt läget är — inte hur mycket de redan gått.")
    st.page_link("views/radar.py", label="Öppna Market Radar", icon="📡")
with b:
    st.markdown("#### 🔎 Bolag i detalj")
    st.write("Ett bolag i taget: färdig slutsats, kursgraf, historiska analoger.")
    st.page_link("views/bolag_detalj.py", label="Öppna Bolag i detalj", icon="🔎")
with c:
    st.markdown("#### 📈 Rörelser & utbrott")
    st.write("De största kursrörelserna just nu — och om något syntes i förväg.")
    st.page_link("views/rorelser.py", label="Öppna Rörelser & utbrott", icon="📈")

st.divider()

with st.expander("Om Noel AI och hur verktyget läses"):
    st.markdown(
        "Noel AI mäter **förändringar i marknadens beteende** kring nordiska "
        "småbolag — handelsvolym, kursmomentum, hur nära årshögsta en aktie handlas "
        "— och testar statistiskt om de förändringarna bär information om "
        "**framtida kursrörelser**. Det är *inte* en prognosmaskin och ger inga "
        "köp- eller säljråd."
    )
    k = kpis()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bolag i databasen", k["n_securities"])
    c2.metric("Varav döda", k["n_dead"], help="Uppköpta, i konkurs eller avnoterade — behålls med i panelen")
    c3.metric("I universum senaste veckan", k["n_in_universe_now"])
    c4.metric("Observationer", f"{k['n_obs']:,}".replace(",", " "), help="Bolag × vecka, 2020–2026")

    st.markdown("**Ordlista**")
    st.markdown(
        "- **Universum** — de nordiska småbolag som uppfyller kraven en given vecka. "
        "Uppköpta och konkursade bolag ligger kvar.\n"
        "- **Uppbyggnadspoäng** — huvudrankningen. Letar läget FÖRE en rörelse. "
        "Experimentell, ovaliderad.\n"
        "- **Discovery Score** — referensmått: hur starkt ett bolag rör sig *just nu*. "
        "Experimentell, ovaliderad.\n"
        "- **Signal / mönster** — ett förregistrerat villkor. Att det \"lyser\" betyder "
        "att bolaget matchar villkoret — inget mer.\n"
        "- **Basnivå** — hur ofta en stor uppgång sker överhuvudtaget, jämförelsepunkten "
        "för allt annat.\n"
        "- **small / mid** — bolag som vuxit förbi small cap-taket taggas *mid* och "
        "hålls utanför huvudanalysen."
    )

    st.markdown("**Hur ofta sker en stor uppgång överhuvudtaget? (basnivåer)**")
    br = base_rates()
    if br.empty:
        st.write("Kör `uv run marc stats` för att fylla i forskningsresultaten.")
    else:
        br = br.copy()
        br["Uppgång"] = br["event"].map(EVENT_CODE_SV).fillna(br["event"])
        piv = br.pivot(index="Uppgång", columns="segment", values="rate")
        st.bar_chart(piv, y_label="andel av veckorna")

    st.markdown("**Teknisk status**")
    st.dataframe(pipeline_status(), hide_index=True, width="stretch")
