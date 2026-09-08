"""Marc AI — internt research-verktyg (v0.1 marknadsbaslinje).

Startfil för Streamlit. Sätter upp navigationen; varje sida ligger i ``app/views/``.
Ingen affärslogik här eller i sidorna — allt kommer från paketet ``marc`` via
``app/_data.py``.
"""

from __future__ import annotations

import os

import streamlit as st

st.set_page_config(page_title="Marc AI", page_icon="📈", layout="wide")

from _data import data_source, db_exists, last_signal_date, latest_obs_date  # noqa: E402
from _gate import require_password  # noqa: E402

require_password()

if not db_exists():
    if os.environ.get("MARC_AUTOBUILD"):
        # hostad (t.ex. Streamlit Cloud): bygg databasen från seed-data vid första besöket
        st.title("Marc AI")
        with st.spinner("Bygger databasen (syntetisk data) — tar ~1 minut, engångsjobb…"):
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
            from marc.pipeline import run_all

            run_all(source="synthetic", reset=False)
        st.cache_data.clear()
        st.rerun()
    st.title("Marc AI")
    st.warning("Databasen är inte byggd ännu. Kör det här i en terminal och ladda om sidan:")
    st.code("uv run marc pipeline --source synthetic --reset", language="bash")
    st.stop()

with st.sidebar:
    st.markdown("### Marc AI")
    st.caption("Internt research-verktyg · nordiska småbolag")
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

pages = [
    st.Page("views/start.py", title="Start", icon="🏠", default=True),
    st.Page("views/bolag.py", title="Bolag", icon="📋"),
    st.Page("views/bolag_detalj.py", title="Bolag i detalj", icon="🔎"),
    st.Page("views/signaler.py", title="Signaler", icon="🚨"),
    st.Page("views/forskning.py", title="Forskning (E1)", icon="🧪"),
]
st.navigation(pages).run()
