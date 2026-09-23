"""Delat utseende för hela appen — ett ställe att justera känslan i stället för
att sprida CSS över alla sidor. Ingen affärslogik här.

``inject_css()`` anropas en gång i ``Home.py`` (körs innan ``st.navigation``,
så CSS:en gäller alla sidor). Färgerna matchar det som redan användes hårdkodat
i pappershandeln (grönt/rött/blått för resultat) — här blir de återanvändbara
konstanter i stället för upprepad hex i varje fil.
"""

from __future__ import annotations

import streamlit as st

GREEN = "#22c55e"
RED = "#ef4444"
BLUE = "#4c8dff"
AMBER = "#f59e0b"
GREY = "#9aa7b0"

_BADGE_COLORS = {
    "green": (GREEN, "rgba(34,197,94,0.12)"),
    "red": (RED, "rgba(239,68,68,0.12)"),
    "blue": (BLUE, "rgba(76,141,255,0.14)"),
    "amber": (AMBER, "rgba(245,158,11,0.14)"),
    "grey": (GREY, "rgba(154,167,176,0.12)"),
}


def pnl_color(v: float | None) -> str:
    """Grönt = plus, rött = minus, blått = exakt +-0, grått = okänt."""
    if v is None:
        return GREY
    try:
        if v != v:  # NaN
            return GREY
    except TypeError:
        return GREY
    if abs(v) < 1e-9:
        return BLUE
    return GREEN if v > 0 else RED


def badge(label: str, kind: str = "grey") -> str:
    """HTML för en liten färgad pill-badge. Använd med ``unsafe_allow_html``."""
    fg, bg = _BADGE_COLORS.get(kind, _BADGE_COLORS["grey"])
    return (
        f"<span style='display:inline-block;padding:2px 10px;border-radius:999px;"
        f"font-size:0.78rem;font-weight:600;color:{fg};background:{bg};"
        f"white-space:nowrap'>{label}</span>"
    )


def render_badge(label: str, kind: str = "grey") -> None:
    st.markdown(badge(label, kind), unsafe_allow_html=True)


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        /* tätare, mer "app"-känsla — mindre bortkastat luftrum överst */
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }}

        /* dölj sånt som avslöjar "det här är ett Streamlit-devverktyg" */
        [data-testid="stAppDeployButton"] {{ display: none; }}
        footer {{ visibility: hidden; }}

        /* rubriker lite fastare/tightare */
        h1, h2, h3 {{ font-weight: 800; letter-spacing: -0.01em; }}
        h1 {{ font-size: 1.9rem !important; }}
        h2 {{ font-size: 1.35rem !important; }}
        h3 {{ font-size: 1.1rem !important; }}

        /* sidopanel: egen ton, tydligare gruppering */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #10131b 0%, #0c0e14 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
        }}
        [data-testid="stSidebar"] hr {{ margin: 0.6rem 0; }}

        /* kort (st.container(border=True)) — mjuk skugga, rundade hörn, lite
           "lyft" — det här är arbetshästen för hela redesignen eftersom
           nästan alla slutsatser nu ligger i ett bordered container. */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 14px !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            background: rgba(255,255,255,0.015);
            box-shadow: 0 1px 3px rgba(0,0,0,0.25);
            transition: border-color 0.15s ease;
        }}
        [data-testid="stVerticalBlockBorderWrapper"]:hover {{
            border-color: rgba(76,141,255,0.35) !important;
        }}

        /* metrics — större siffra, tystare etikett, som ett mäklarkort */
        [data-testid="stMetricLabel"] {{
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            opacity: 0.65;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 1.65rem !important;
            font-weight: 800 !important;
        }}

        /* knappar — rundare, tydligare primärfärg */
        .stButton > button {{
            border-radius: 10px;
            font-weight: 600;
        }}
        .stButton > button[kind="primary"] {{
            background: {BLUE};
            border-color: {BLUE};
        }}

        /* dataframe/tabell-wrapper — rundade hörn så det känns som en produkt */
        [data-testid="stDataFrame"] {{
            border-radius: 12px;
            overflow: hidden;
        }}

        /* progressbars (Uppbyggnad/Discovery) — tunnare, rundare */
        .stProgress > div > div {{ border-radius: 999px; }}
        .stProgress > div {{ border-radius: 999px; background: rgba(255,255,255,0.08); }}

        /* expander — plattare, mindre "låda i låda"-känsla */
        [data-testid="stExpander"] {{
            border-radius: 12px !important;
            border: 1px solid rgba(255,255,255,0.07) !important;
        }}

        /* dividers lite tystare */
        hr {{ border-color: rgba(255,255,255,0.08) !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def big_number(label: str, value: str, color: str, sub: str | None = None) -> None:
    """Ett stort, färgat nyckeltal i Avanza-stil (för resultat i kr/procent
    där Streamlits inbyggda ``st.metric`` inte kan färgas fritt)."""
    sub_html = f"<div style='font-size:1rem;font-weight:600;color:{color}'>{sub}</div>" if sub else ""
    st.markdown(
        f"<div style='font-size:0.78rem;font-weight:600;text-transform:uppercase;"
        f"letter-spacing:0.03em;opacity:0.65;margin-bottom:2px'>{label}</div>"
        f"<div style='font-size:1.75rem;font-weight:800;color:{color};line-height:1.2'>{value}</div>"
        f"{sub_html}",
        unsafe_allow_html=True,
    )
