"""Noel AI — internt research-verktyg för nordiska småbolag.

Market discovery / market psychology: mäter förändringar i uppmärksamhet, volym
och momentum, placerar bolag i en hype-cykel och jämför nuläget med historiska
analoger. Startfil för Streamlit — ingen affärslogik här eller i sidorna, allt
kommer från paketet ``marc`` via ``app/_data.py``.
"""

from __future__ import annotations

import os

import streamlit as st

st.set_page_config(page_title="Noel AI", page_icon="📡", layout="wide")

from _data import data_source, db_exists, last_signal_date, latest_obs_date  # noqa: E402
from _gate import require_password  # noqa: E402

require_password()

if not db_exists():
    # Ingen databasfil (t.ex. färsk deploy på Streamlit Cloud). Bygg den vid
    # första besöket. MARC_DATA_SOURCE styr källa (default "yfinance", riktig
    # data; faller tillbaka till "synthetic" om nätet/Yahoo inte går att nå).
    # MARC_AUTOBUILD="0" stänger av auto-bygget helt.
    if os.environ.get("MARC_AUTOBUILD", "1") != "0":
        st.title("Noel AI")
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        from marc.pipeline import run_all

        want = os.environ.get("MARC_DATA_SOURCE", "yfinance")
        built = False
        if want == "yfinance":
            try:
                with st.spinner(
                    "Hämtar riktig kursdata och bygger databasen — tar ~2–4 minuter, engångsjobb…"
                ):
                    run_all(source="yfinance", reset=False)
                built = True
            except Exception as exc:  # noqa: BLE001 - nät/Yahoo kan strula på hostad miljö
                st.warning(f"Kunde inte hämta riktig data ({exc}). Bygger med syntetisk data i stället.")
        if not built:
            try:
                with st.spinner("Bygger databasen (syntetisk data) — tar ~1–2 minuter, engångsjobb…"):
                    run_all(source="synthetic", reset=False)
                built = True
            except Exception as exc:  # noqa: BLE001 - visa felet i stället för en tyst vägg
                st.error(f"Bygget av databasen misslyckades: {exc}")
                st.caption("Ladda om sidan för att försöka igen, eller bygg manuellt lokalt.")
                st.code("uv run marc pipeline --source yfinance --reset", language="bash")
                st.stop()
        st.cache_data.clear()
        st.rerun()
    st.title("Noel AI")
    st.warning("Databasen är inte byggd ännu. Kör det här i en terminal och ladda om sidan:")
    st.code("uv run marc pipeline --source yfinance --reset", language="bash")
    st.stop()

with st.sidebar:
    st.markdown("### 📡 Noel AI")
    st.caption("Market discovery · nordiska småbolag")
    if data_source() == "synthetic":
        st.caption(
            "⚠️ **Syntetisk data** – inte marknadsdata. Alla siffror är exempel "
            "för att testa systemet."
        )
    d = latest_obs_date()
    ls = last_signal_date()
    if d is not None:
        st.caption(f"Senaste datavecka: **{d:%Y-%m-%d}**")
    if ls is not None:
        st.caption(f"Senaste signalvecka: **{ls:%Y-%m-%d}**")
    st.caption(
        "Experimentellt researchverktyg. Ingenting här är validerat eller "
        "investeringsrådgivning."
    )

nav = {
    "Radar": [
        st.Page("views/radar.py", title="Market Radar", icon="📡", default=True),
        st.Page("views/dagens.py", title="Dagens upptäckter", icon="🌅"),
    ],
    "Bolag": [
        st.Page("views/bolag.py", title="Alla bolag", icon="📋"),
        st.Page("views/bolag_detalj.py", title="Bolag i detalj", icon="🔎"),
        st.Page("views/rorelser.py", title="Rörelser & utbrott", icon="📈"),
    ],
    "Forskning": [
        st.Page("views/signal_lab.py", title="Signal Lab", icon="🧪"),
        st.Page("views/signaler.py", title="Signaler", icon="🚨"),
        st.Page("views/forskning.py", title="Forskning (E1)", icon="📚"),
    ],
    "Noel": [
        st.Page("views/performance.py", title="Performance", icon="📊"),
    ],
}
st.navigation(nav).run()
