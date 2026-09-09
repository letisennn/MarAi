"""Startsida — vad verktyget är och vart man tar vägen."""

from __future__ import annotations

import streamlit as st

from _data import EVENT_CODE_SV, base_rates, data_source, kpis, pipeline_status

st.title("📡 Noel AI")

st.markdown(
    "Noel AI mäter **förändringar i marknadens beteende** kring nordiska "
    "småbolag — handelsvolym, kursmomentum, rörlighet, hur nära årshögsta en "
    "aktie handlas — och testar statistiskt om de förändringarna bär information "
    "om **framtida kursrörelser**.\n\n"
    "Det är *inte* en prognosmaskin och ger inga köp- eller säljråd. Verktyget "
    "svarar på frågan *bär de här mätningarna någon användbar information alls?* "
    "— och \"nej\" är ett giltigt svar."
)

if data_source() == "synthetic":
    st.warning(
        "**Syntetisk data.** Priserna är deterministiska pseudo-slumpbanor, inte "
        "marknadsdata — de finns för att köra och demonstrera hela kedjan. Läs "
        "alla siffror i appen som *exempel på utdataform*, inte som resultat, "
        "tills en riktig priskälla kopplats in."
    )

k = kpis()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Bolag i databasen", k["n_securities"])
c2.metric("Varav döda", k["n_dead"], help="Uppköpta, i konkurs eller avnoterade — behålls med i panelen")
c3.metric("I universum senaste veckan", k["n_in_universe_now"])
c4.metric("Observationer", f"{k['n_obs']:,}".replace(",", " "), help="Bolag × vecka, 2020–2026")

st.divider()
st.subheader("Vart tar jag vägen?")
a, b, c = st.columns(3)
with a:
    st.markdown("#### 📋 Bolag")
    st.write(
        "Alla bolag i en tabell — börsvärde, momentum, volym och hur många "
        "mönster som lyst de senaste veckorna. Sök, filtrera och sortera."
    )
    st.page_link("views/bolag.py", label="Öppna Bolag", icon="📋")
with b:
    st.markdown("#### 🔎 Bolag i detalj")
    st.write(
        "Ett bolag i taget: kursgraf, vad Noel mäter just nu i klartext, och "
        "när förregistrerade mönster har lyst tidigare."
    )
    st.page_link("views/bolag_detalj.py", label="Öppna Bolag i detalj", icon="🔎")
with c:
    st.markdown("#### 🚨 Signaler")
    st.write(
        "Vilka bolag matchar ett förregistrerat mönster de senaste veckorna — "
        "och hur det har gått historiskt jämfört med slumpen."
    )
    st.page_link("views/signaler.py", label="Öppna Signaler", icon="🚨")

st.divider()

with st.expander("Så läser du verktyget (ordlista)"):
    st.markdown(
        "- **Universum** — de nordiska småbolag som uppfyller kraven (börsvärde "
        "50 MSEK–1,7 Bn SEK, tillräcklig handel, minst ett års historik) en given "
        "vecka. Listan ändras över tid; uppköpta och konkursade bolag ligger kvar.\n"
        "- **Observation** — ett bolag vid ett veckoslut. All analys utgår från "
        "observationer.\n"
        "- **Mått (feature)** — något som mäts *med enbart historik fram till "
        "veckan*, t.ex. avkastning 3 månader eller relativ volym. Aldrig något "
        "framåtblickande.\n"
        "- **Utfall (target)** — vad som *sedan* hände, t.ex. avkastning 90 dagar "
        "framåt. Används bara för att utvärdera mått — matas aldrig tillbaka in.\n"
        "- **Signal / regel** — ett förregistrerat villkor. Att en regel \"lyser\" "
        "betyder att bolaget matchar villkoret — inget mer.\n"
        "- **Discovery Score** — en **experimentell** poäng 0–100 per aktie som väger "
        "momentum, läge mot årshögsta, handel och mönster. Vikterna är handsatta "
        "och *ovaliderade* — ett arbetsverktyg, inte ett facit. Byts mot en "
        "statistiskt/ML-härledd vikt när E1 säger sitt.\n"
        "- **Basnivå** — hur ofta en stor uppgång sker överhuvudtaget. "
        "Jämförelsepunkten för allt annat.\n"
        "- **Holdout** — en avskild senare period (2025-01→2026-06) som bara "
        "utvärderas en gång, för att inte lura sig själv.\n"
        "- **small / mid** — bolag som vuxit förbi small cap-taket taggas *mid* och "
        "hålls utanför huvudanalysen, men finns kvar för separata studier."
    )

with st.expander("Hur ofta sker en stor uppgång överhuvudtaget? (basnivåer)"):
    st.caption(
        "Andel veckoobservationer som nådde respektive uppgång inom sitt fönster. "
        "`small` = genuina småbolag (huvudsiffran). `mid` = bolag som vuxit ur "
        "small cap, visas för jämförelse."
    )
    br = base_rates()
    if br.empty:
        st.write("Kör `uv run marc stats` för att fylla i forskningsresultaten.")
    else:
        br = br.copy()
        br["Uppgång"] = br["event"].map(EVENT_CODE_SV).fillna(br["event"])
        piv = br.pivot(index="Uppgång", columns="segment", values="rate")
        st.bar_chart(piv, y_label="andel av veckorna")
        st.dataframe(
            br[["Uppgång", "segment", "rate", "ci_low", "ci_high", "n_obs", "n_events"]].rename(
                columns={
                    "segment": "Segment",
                    "rate": "Andel",
                    "ci_low": "KI låg",
                    "ci_high": "KI hög",
                    "n_obs": "Antal obs",
                    "n_events": "Antal träffar",
                }
            ),
            hide_index=True,
            width="stretch",
        )

with st.expander("Teknisk status (för oss som bygger)"):
    st.dataframe(pipeline_status(), hide_index=True, width="stretch")
    st.caption(
        "Bygg om allt: `uv run marc pipeline --source synthetic --reset`. "
        "Byt till riktig (survivorship-biased) prisdata: `--source yfinance`."
    )
