"""Noteringar på pappersaffärer (Jonas, 2026-09-23).

Varje affär kan ha en egen anteckning ("varför") som man skriver och ändrar
själv, plus en automatisk ögonblicksbild som Noel sparar när affären görs:
fas, volym, Noels slutsats och nyckeltal. Ögonblicksbilden är läget DÅ — den
skrivs aldrig om i efterhand. Ikonen 📝 öppnar allt i en popover.
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

import _paper


def _sek(v) -> str:
    if v is None or v != v:
        return "–"
    return f"{v:,.0f} kr".replace(",", " ")


def _pct(v, plus: bool = True, dec: int = 0) -> str:
    if v is None or v != v:
        return "–"
    return f"{v * 100:+.{dec}f} %" if plus else f"{v * 100:.{dec}f} %"


def parse_snapshot(raw) -> dict | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)) or not str(raw).strip():
        return None
    try:
        snap = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (TypeError, ValueError):
        return None
    return snap if isinstance(snap, dict) else None


def snapshot_markdown(snap: dict, side: str) -> str:
    """Ögonblicksbilden i klartext: fas, volym, Noels nyckeltal."""
    when = "köp" if side == "buy" else "sälj"
    lines = [f"**📸 Läget vid {when}** — {str(snap.get('tagen', ''))[:16].replace('T', ' ')} "
             f"(Noels veckodata: {snap.get('data_vecka') or '–'})"]

    fas = snap.get("fas") or {}
    if fas.get("namn"):
        lines.append(f"- **Fas:** {fas.get('markering') or ''} {fas['namn']} — {fas.get('beskrivning') or ''}")

    v = snap.get("volym") or {}
    if v:
        mn = v.get("mot_normalt")
        rel = (f"{abs(mn - 1) * 100:.0f} % {'över' if mn > 1 else 'under'} normalt" if mn else "okänd nivå mot normalt")
        trend = f", {v['trend']}" if v.get("trend") else ""
        lines.append(
            f"- **Volym:** handeln senaste 5 dagarna låg {rel}{trend}. Senaste dagen ({v.get('senaste_dag')}): "
            f"{v.get('senaste_dag_aktier') and int(v['senaste_dag_aktier']):,} aktier ≈ {_sek(v.get('senaste_dag_omsattning_sek'))}; ".replace(",", " ")
            + f"snitt 5 dagar {_sek(v.get('snitt_5d_omsattning_sek'))}, median 60 dagar {_sek(v.get('median_60d_omsattning_sek'))} per dag."
        )

    n = snap.get("noel") or {}
    if n.get("slutsats"):
        lines.append(f"- **Noels slutsats:** {n.get('ikon') or ''} **{n['slutsats']}** — {n.get('sammanfattning') or ''}")
    up = n.get("uppbyggnad")
    if up:
        vis = " — redan synligt för alla" if up.get("redan_synligt") else ""
        lines.append(f"- **Uppbyggnadspoäng:** {up['poang']:.0f}/100 ({up['band']}){vis}")
    dc = n.get("discovery")
    if dc:
        lines.append(f"- **Discovery Score (referens):** {dc['poang']:.0f}/100 ({dc['band']})")
    if n.get("monster_lyst"):
        lines.append(f"- **Förregistrerade mönster som lyst:** {', '.join(n['monster_lyst'])}")

    k = snap.get("nyckeltal") or {}
    parts = [f"1 mån {_pct(k.get('kurs_1m'))}", f"3 mån {_pct(k.get('kurs_3m'))}", f"12 mån {_pct(k.get('kurs_12m'))}",
             f"från årshögsta {_pct(k.get('fran_arshogsta'))}"]
    lines.append("- **Kurs:** " + " · ".join(parts))
    extra = []
    if k.get("volatilitet_20d") is not None:
        extra.append(f"volatilitet {_pct(k['volatilitet_20d'], plus=False)} (årstakt)")
    if k.get("sok_acceleration") is not None:
        extra.append(f"sökintresse {_pct(k['sok_acceleration'])} mot en månad sedan")
    if k.get("nyhetston_z") is not None:
        extra.append(f"nyhetston z {k['nyhetston_z']:+.1f}")
    if extra:
        lines.append("- **Övrigt:** " + " · ".join(extra))

    if n.get("tidshorisont"):
        lines.append(f"- **⏱ Tidshorisont:** {n['tidshorisont']}")
    if n.get("ogiltigt_om"):
        lines.append(f"- **🚫 Ogiltigt om:** {n['ogiltigt_om']}")
    if n.get("historik"):
        lines.append(f"- **Historik för det här läget:** {n['historik']}")
    return "\n".join(lines)


def notes_popover(owner: str, trades: list[dict], title: str, key_prefix: str) -> None:
    """📝-ikonen: öppnar noteringar + ögonblicksbild för en eller flera affärer."""
    with st.popover("📝", help="Visa/skriv noteringar och se läget vid affären"):
        st.markdown(f"**{title}**")
        for t in trades:
            side = t["side"]
            tid = int(t["trade_id"])
            st.markdown(
                f"##### {'Köp' if side == 'buy' else 'Sälj'} {str(t['trade_date'])[:10]} · "
                f"{t['shares']:.0f} st @ {t['price_sek']:.2f} kr"
            )
            note_key = f"note_{key_prefix}_{tid}"
            text = st.text_area(
                "Din notering", value=t.get("note") or "", key=note_key, height=90,
                placeholder="Varför köpte/sålde du? Mål, stop, tid…", label_visibility="collapsed",
            )
            if st.button("Spara notering", key=f"save_{key_prefix}_{tid}"):
                _paper.set_note(owner, tid, text)
                # andra 📝-rutor för samma affär ska inte visa gammal text
                for k in [k for k in st.session_state if k.startswith("note_") and k.endswith(f"_{tid}")]:
                    if k != note_key:
                        del st.session_state[k]
                st.session_state["_toast_msg"] = "Noteringen sparad"
                st.rerun()
            snap = parse_snapshot(t.get("snapshot"))
            if snap:
                st.markdown(snapshot_markdown(snap, side))
            else:
                st.caption("Ingen automatisk bild sparad — affären gjordes innan noteringsfunktionen fanns.")
            st.divider()
