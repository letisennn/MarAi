"""Enkel lösenordsspärr för appen när den exponeras utanför localhost.

Aktiveras bara om ``MARC_APP_PASSWORD`` är satt — antingen som miljövariabel
(lokalt) eller i Streamlit-appens *Secrets* (hostad). Utan den satt händer
ingenting. Inte riktig auth — bara ett delat lösenord så att en delad länk inte
ligger helt öppen.
"""

from __future__ import annotations

import hmac
import os

import streamlit as st


def _configured_password() -> str:
    """Läs lösenordet från Streamlit-secrets om det finns där, annars miljön."""
    try:
        val = st.secrets.get("MARC_APP_PASSWORD")  # type: ignore[attr-defined]
        if val:
            return str(val)
    except Exception:  # noqa: BLE001 - inga secrets konfigurerade => faller igenom
        pass
    return os.environ.get("MARC_APP_PASSWORD", "")


def require_password() -> None:
    secret = _configured_password()
    if not secret:
        return
    if st.session_state.get("_auth_ok"):
        return

    st.title("Noel AI")
    st.caption("Internt verktyg. Ange lösenordet för att fortsätta.")
    pw = st.text_input("Lösenord", type="password")
    if pw and hmac.compare_digest(pw, secret):
        st.session_state["_auth_ok"] = True
        st.rerun()
    elif pw:
        st.error("Fel lösenord.")
    st.stop()
