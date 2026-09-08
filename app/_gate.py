"""Enkel lösenordsspärr för appen när den exponeras utanför localhost.

Aktiveras bara om miljövariabeln ``MARC_APP_PASSWORD`` är satt. Lokalt (utan den
satt) händer ingenting. Inte riktig auth — bara ett delat lösenord så att en
delad länk (tunnel etc.) inte ligger helt öppen.
"""

from __future__ import annotations

import hmac
import os

import streamlit as st


def require_password() -> None:
    secret = os.environ.get("MARC_APP_PASSWORD", "")
    if not secret:
        return
    if st.session_state.get("_auth_ok"):
        return

    st.title("Marc AI")
    st.caption("Internt verktyg. Ange lösenordet för att fortsätta.")
    pw = st.text_input("Lösenord", type="password")
    if pw and hmac.compare_digest(pw, secret):
        st.session_state["_auth_ok"] = True
        st.rerun()
    elif pw:
        st.error("Fel lösenord.")
    st.stop()
