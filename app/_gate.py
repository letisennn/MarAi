"""Inloggning — Jonas och Hugo, var sitt konto och lösenord.

Ersätter det gamla delade ``MARC_APP_PASSWORD`` (2026-09-19, Jonas): två
namngivna konton istället för ett delat lösenord och en fri "välj vem du
är"-ruta. Vem som är inloggad styr pappershandelns separata konton
(``marc.paper``) — inloggningen bevisar identiteten, appen litar inte bara på
vad man klickar i sidopanelen.

Lösenorden läses från Streamlit-secrets (hostad app) eller miljövariabler
(lokalt, via ``.env``) — ALDRIG hårdkodade i källkoden, eftersom repot är
publikt på GitHub (se docs/deploy.md). Sätt ``MARC_USER_JONAS_PASSWORD`` /
``MARC_USER_HUGO_PASSWORD`` i din egen ``.env`` (gitignorerad).

Inte riktig säkerhet i djupare mening (samma nivå som förut) — bara till för
att inte handla på fel persons pappersportfölj.
"""

from __future__ import annotations

import hmac
import os
import time

import streamlit as st

USERS = {"jonas": "Jonas", "hugo": "Hugo"}

# Bromsar gissning av lösenord när appen ligger på en publik adress (2026-09-24):
# efter MAX_FAILS felaktiga försök inom WINDOW sekunder låses inloggningen för
# den användaren i LOCK sekunder. Delas av alla besökare (en per serverprocess),
# så det går inte att gå runt genom att öppna en ny flik.
MAX_FAILS = 5
WINDOW = 600
LOCK = 300


@st.cache_resource
def _failed_attempts() -> dict[str, list[float]]:
    return {}


def _locked_for(user: str, now: float | None = None) -> int:
    """Sekunder kvar av en låsning (0 = ej låst)."""
    now = time.time() if now is None else now
    fails = [t for t in _failed_attempts().get(user, []) if now - t < WINDOW]
    _failed_attempts()[user] = fails
    if len(fails) >= MAX_FAILS:
        return max(0, int(fails[-1] + LOCK - now))
    return 0


def _register_failure(user: str, now: float | None = None) -> None:
    _failed_attempts().setdefault(user, []).append(time.time() if now is None else now)


def _configured_password(user: str) -> str:
    """Läs lösenordet för ``user`` från Streamlit-secrets om det finns, annars miljön."""
    env_key = f"MARC_USER_{user.upper()}_PASSWORD"
    try:
        val = st.secrets.get(env_key)  # type: ignore[attr-defined]
        if val:
            return str(val)
    except Exception:  # noqa: BLE001 - inga secrets konfigurerade => faller igenom
        pass
    return os.environ.get(env_key, "")


def current_user() -> str | None:
    """``"jonas"`` / ``"hugo"`` om någon är inloggad, annars ``None``."""
    u = st.session_state.get("_auth_user")
    return u if u in USERS else None


def logout() -> None:
    st.session_state.pop("_auth_user", None)
    st.rerun()


def require_login() -> None:
    """Stoppar sidan tills någon loggat in som Jonas eller Hugo.

    Om inget av lösenorden är konfigurerat (t.ex. lokal körning utan
    ``.env``) släpps Jonas igenom utan spärr, så utveckling inte fastnar —
    samma "ingenting händer om inget är satt"-princip som den gamla spärren.
    """
    configured = [u for u in USERS if _configured_password(u)]
    if not configured:
        st.session_state.setdefault("_auth_user", "jonas")
        return
    if current_user() is not None:
        return

    st.title("📡 Noel AI")
    st.caption("Internt verktyg. Logga in för att fortsätta.")
    with st.form("login"):
        user = st.radio("Vem är du?", list(USERS), format_func=lambda u: USERS[u], horizontal=True)
        pw = st.text_input("Lösenord", type="password")
        submitted = st.form_submit_button("Logga in", type="primary")
    if submitted:
        left = _locked_for(user)
        secret = _configured_password(user)
        if left:
            st.error(f"För många felaktiga försök — inloggningen är låst i ca {left} s till.")
        elif secret and pw and hmac.compare_digest(pw, secret):
            _failed_attempts().pop(user, None)
            st.session_state["_auth_user"] = user
            st.rerun()
        else:
            _register_failure(user)
            st.error("Fel lösenord.")
    st.stop()
