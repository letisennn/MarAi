"""Köpguider — vad varje sida betyder för den som ska KÖPA.

Jonas, 2026-09-23: "skriv för varje rubrik vad det innebär för oss som vill köpa
— vad ska vi leta efter, target, tidshorisont … för nu ger den random info".

Alla siffror kommer ur playbooken (E1e, ``marc stats``): utfall räknade från
köpkursen (stängning dag t) för småbolag 2022–2026, uppdelat på lägen. Ingen
målnivå eller tid är påhittad — det som står är vad som faktiskt hänt efter
samma läge tidigare. Beskrivande historik, ingen prognos.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from _data import playbook_row

_BASE = ("all", "Alla bolag (basnivå)")
_MISSING = "Playbook-siffrorna saknas — kör `uv run marc stats` för att räkna fram dem."

PAGE_MAP = """
| Sida | Frågan den svarar på | Använd den när du … | Den säger INTE |
|---|---|---|---|
| **Dagens upptäckter** | Vilka ~8 bolag är mest intressanta *just nu*? | vill ha en kortlista att börja med | att något ska stiga |
| **Market Radar** | Vilka av *alla* bolag bygger upp tyst — **innan** en rörelse? | letar kandidater och vill jämföra/filtrera | vilka som blir vinnare |
| **Rörelser & utbrott** | Vad har **redan** rört sig kraftigt — och syntes något i förväg? | vill förstå vad marknaden köper, eller undvika att jaga | att du ska köpa det som stigit |
| **Alla bolag** | Hur ser ett visst bolag ut i listan? | slår upp/jämför bolag | — |
| **Bolag i detalj** | Vad tror Noel om *det här* bolaget, och när är tesen fel? | ska ta ett beslut om ett bolag | en garanti |
| **Paperhandel** | Hur hade det gått om jag köpt? | övar med fejkade pengar innan riktiga | — |
"""


def _pct(x: float | None, plus: bool = False, dec: int = 0) -> str:
    if x is None or x != x:
        return "–"
    v = x * 100
    return f"{v:+.{dec}f} %" if plus else f"{v:.{dec}f} %"


def stats_table(items: list[tuple[str, str, str]], horizon: int = 20) -> pd.DataFrame | None:
    """En rad per läge: (etikett, group_type, group) -> köparens utfall."""
    rows = []
    for label, gtype, group in items:
        r = playbook_row(gtype, group, horizon)
        if not r:
            continue
        d = r.get("med_days_to_peak_30")
        rows.append({
            "Läge": label,
            "Plus efter": _pct(r["win_rate"]),
            "Median": _pct(r["median_ret"], plus=True, dec=1),
            "Typisk bästa punkt": _pct(r["med_max_ret"], plus=True),
            "Typisk sämsta dipp": _pct(r["med_max_dd"], plus=True),
            "Nådde +10 %": _pct(r["p_reach_10"]),
            "Nådde +25 %": _pct(r["p_reach_25"]),
            "Dippade −10 %": _pct(r["p_dip_10"]),
            "Tid till topp": f"~{d:.0f} h-dagar" if d else "–",
            "Antal": f"{int(r['n']):,}".replace(",", " "),
        })
    return pd.DataFrame(rows) if rows else None


def _show(df: pd.DataFrame | None, note: str | None = None) -> None:
    if df is None:
        st.caption(_MISSING)
        return
    st.dataframe(df, hide_index=True, width="stretch")
    if note:
        st.caption(note)


def _leverage_line(row: dict | None, row5: dict | None) -> str:
    if not row:
        return ""
    txt = (
        f"**Med 10x hävstång:** en dipp på 10 % slår ut hela insatsen. I det här läget hade "
        f"**{_pct(row['p_dip_10'])}** av fallen dippat så mycket inom 20 handelsdagar"
    )
    if row5:
        txt += f" (och {_pct(row5['p_dip_10'])} redan inom 5)"
    return txt + ". Dippar under dagen är djupare än siffrorna visar (glesa handelsdagar filtreras bort) — och en analys på veckodata kan aldrig ge en exakt tid för intradagsaffärer."


CAVEATS = (
    "Beskrivande historik, inte en prognos. Universumet är survivorship-biased (bara bolag som "
    "finns kvar) så siffrorna är om något för *optimistiska*; courtage och spread i småbolag är inte "
    "avdragna; överlappande fönster gör att träffarna inte är oberoende."
)


def _box(title: str, expanded: bool = True):
    return st.expander(title, expanded=expanded)


# ------------------------------------------------------------------ Market Radar
def radar_guide() -> None:
    with _box("🎯 Så använder du Market Radar när du ska köpa"):
        st.markdown(
            "**Vad sidan gör:** rankar *alla* bolag på hur tydligt de **bygger upp tyst** — stigande "
            "volym/uppmärksamhet, lugn kurs, en bit under årshögsta. Alltså läget **före** en rörelse. "
            "**Skillnad mot Rörelser & utbrott:** Radar tittar på det som *ännu inte* hänt; Rörelser visar det "
            "som *redan* hänt. Radar är för att hitta kandidater, Rörelser för att förstå vad marknaden köper."
        )
        st.markdown("**Vad har varje läge historiskt betytt för en köpare?** (efter 20 handelsdagar)")
        bands = [
            ("🔥 Mycket starkt setup", "band", "Mycket starkt setup"),
            ("📈 Starkt setup", "band", "Starkt setup"),
            ("🌱 Tidigt setup", "band", "Tidigt setup"),
            ("🔎 Bevaka", "band", "Bevaka"),
            ("⚪ Inget setup", "band", "Inget setup"),
            ("⚠️ Redan synligt", "band", "Redan synligt"),
            ("Alla bolag (basnivå)", *_BASE),
        ]
        _show(stats_table(bands, 20), "Median = typiskt utfall. Bästa punkt/dipp = median av högsta/lägsta kurs inom 20 dagar mot köpkursen.")

        best, base = playbook_row("band", "Starkt setup", 20), playbook_row(*_BASE, 20)
        best5 = playbook_row("band", "Starkt setup", 5)
        if best and base:
            d = best.get("med_days_to_peak_30") or 12
            st.markdown(
                f"""
**Vad du ska gå för:** bolag i **Starkt** eller **Mycket starkt setup**. **Undvik** *Inget setup* och *Bevaka* — de är
de mest svängiga och har sämst odds.

**Ärligt om oddsen:** även bästa banden har median nära 0 % efter 20 dagar. Poängen *flyttar oddsen* (lägre risk,
något bättre träffchans: {_pct(best['win_rate'])} på plus mot {_pct(base['win_rate'])} i snitt) — den hittar inga garanterade
vinnare. Småbolag som helhet har historiskt oftare slutat på minus än på plus.

**Målnivå:** typisk bästa punkt inom 20 dagar är **{_pct(best['med_max_ret'], plus=True)}**. {_pct(best['p_reach_10'])} nådde +10 %,
bara {_pct(best['p_reach_25'])} nådde +25 %. Radarns bolag är lugnare — räkna inte med raketer, sätt målet nära +6–10 %.

**Tidshorisont:** toppen kom i median efter ~**{d:.0f} handelsdagar (≈ {d / 5:.0f} veckor)**. Planera att utvärdera efter 2–3 veckor,
inte hålla "för alltid". Signalerna bygger på veckodata — inte intradag.

**Exit:** typisk sämsta dipp är {_pct(best['med_max_dd'], plus=True)}; ett stop runt −8 % ger utrymme för normalt brus.
Sälj också om bolagets **"Ogiltigt om"** (på bolagssidan) inträffar — då är tesen bruten, oavsett kurs.

{_leverage_line(best, best5)}
"""
            )
        st.markdown(
            "**Gör så här:** 1) välj Starkt/Mycket starkt setup (filtret \"Dölj redan synliga\" på) → 2) öppna bolaget och läs "
            "slutsats + *Ogiltigt om* → 3) kolla analoger, nyheter och attention → 4) bestäm **mål, stop och tid innan** du köper → "
            "5) öva först i Paperhandel."
        )
        st.caption(
            "Om edgen: Uppbyggnadspoängens rang-korrelation med framtida avkastning är liten (≈ 0,04) men statistiskt "
            "säkerställd även på 2025-data som den inte byggdes på — en lutning i oddsen, inte ett facit. " + CAVEATS
        )
        with st.expander("🧭 Vilken sida ska jag använda?"):
            st.markdown(PAGE_MAP)


# ------------------------------------------------------------ Rörelser & utbrott
def rorelser_guide(window: str) -> None:
    with _box("🎯 Så använder du Rörelser & utbrott när du ska köpa"):
        st.markdown(
            "**Vad sidan gör:** visar det som **redan** rört sig mest. **Skillnad mot Market Radar:** Radar letar tyst "
            "uppbyggnad *före* en rörelse; den här sidan visar rörelsen *efter* att den skett — och om något syntes i förväg."
        )
        items = [
            ("Topp 10 % uppgång 1 vecka", "mover", "Topp 10 % uppgång 1w"),
            ("Topp 10 % uppgång 1 månad", "mover", "Topp 10 % uppgång 1m"),
            ("Topp 10 % uppgång 3 månader", "mover", "Topp 10 % uppgång 3m"),
            ("Topp 10 % uppgång 12 månader", "mover", "Topp 10 % uppgång 12m"),
            ("1 mån + volym ≥ 2× normalt", "mover", "Topp 10 % uppgång 1m + volym ≥ 2× normalt"),
            ("1 mån, redan vid årshögsta", "mover", "Topp 10 % uppgång 1m, redan vid årshögsta"),
            ("1 mån, fortf. >15 % under årshögsta", "mover", "Topp 10 % uppgång 1m, fortf. >15 % under årshögsta"),
            ("⚡ Nära utbrott (Noels slutsats)", "verdict", "Nära utbrott"),
            ("🚀 Utbrott pågår (Noels slutsats)", "verdict", "Utbrott pågår"),
            ("Alla bolag (basnivå)", *_BASE),
        ]
        t20, t5 = st.tabs(["Efter 20 handelsdagar", "Efter 5 handelsdagar"])
        with t20:
            _show(stats_table(items, 20), "Köp på stängningen den vecka rörelsen syntes. Median = typiskt utfall.")
        with t5:
            _show(stats_table(items, 5))

        win = {"1w": "1w", "1m": "1m", "3m": "3m", "12m": "12m"}[window]
        sel, base = playbook_row("mover", f"Topp 10 % uppgång {win}", 20), playbook_row(*_BASE, 20)
        if sel and base:
            worse = sel["median_ret"] < base["median_ret"]
            st.markdown(
                f"**Det här betyder det för dig:** att köpa bolag *efter* en stor uppgång ({window}) har historiskt gett "
                f"**{'sämre' if worse else 'bättre'} odds än snittet** — {_pct(sel['win_rate'])} på plus efter 20 dagar mot "
                f"{_pct(base['win_rate'])}, median {_pct(sel['median_ret'], plus=True, dec=1)} mot {_pct(base['median_ret'], plus=True, dec=1)}, "
                f"och {_pct(sel['p_dip_10'])} dippade minst −10 % (snittet: {_pct(base['p_dip_10'])}). "
                + ("**Jaga inte uppgångar.**" if worse else "")
            )
        near = playbook_row("verdict", "Nära utbrott", 20)
        if near:
            d = near.get("med_days_to_peak_30") or 14
            st.markdown(
                f"""
**Vad sidan ÄR bra för:**
1. **Se vad marknaden köper** — sektorer och teman som återkommer bland de största rörelserna (kolumnen *Sektor*) är sentimentet.
2. **Lär dig förvarningarna** — "Vad syntes i förväg?" längst ner visar om volym/uppmärksamhet tickade upp *före* rörelsen.
3. **Undvik att jaga** — om du ser ett bolag du missade: siffrorna ovan säger att det oftast är för sent.

**Om du ändå vill handla ett utbrott:** bara läget **⚡ Nära utbrott** (nära årshögsta, stigande handel, *innan* utbrottet) har hållit
sig — {_pct(near['win_rate'])} på plus efter 20 dagar, median {_pct(near['median_ret'], plus=True, dec=1)}, men bara {_pct(near['p_dip_10'])} dippade −10 %
(basnivå: {_pct(playbook_row(*_BASE, 20)['p_dip_10'])}). Målnivå: typisk bästa punkt {_pct(near['med_max_ret'], plus=True)}. Tidshorisont: toppen
i median efter ~{d:.0f} handelsdagar (≈ {d / 5:.0f} veckor). Exit: ogiltigt om kursen faller >8 % utan att volymen fortsätter öka.
Utbrott som *redan pågår* (🚀) har sämre profil: stora svängningar åt båda håll — se tabellen.

{_leverage_line(near, playbook_row('verdict', 'Nära utbrott', 5))}
"""
            )
        st.caption(CAVEATS)
        with st.expander("🧭 Vilken sida ska jag använda?"):
            st.markdown(PAGE_MAP)


# -------------------------------------------------------------- Dagens upptäckter
def dagens_guide() -> None:
    with _box("🎯 Så använder du Dagens upptäckter när du ska köpa", expanded=False):
        st.markdown(
            "**Vad sidan är:** de ~8 bolag Radar rankar högst bland bolag i tidig/accelererande fas som **inte redan syns** för alla. "
            "Använd den som **kortlista** — inte som köporder. Varje kort visar *varför*, *ogiltigt om* (ditt sälj-villkor) och historiska analoger."
        )
        _show(stats_table([
            ("📈 Starkt setup", "band", "Starkt setup"),
            ("🌱 Tidigt setup", "band", "Tidigt setup"),
            ("Alla bolag (basnivå)", *_BASE),
        ], 20), "Efter 20 handelsdagar, köp på stängningen. Typisk topp ca 2–3 veckor efter signalen.")
        st.markdown(
            "**Gör så här:** öppna kortet → läs *Ogiltigt om* → bestäm mål (≈ +6–10 %), stop (≈ −8 %) och tid (2–3 veckor) **innan** du köper. "
            "Skillnad mot Market Radar: samma rankning, men förfiltrerad och med förklaring per bolag."
        )
        st.caption(CAVEATS)


# --------------------------------------------------------------- Bolag i detalj
def detalj_guide() -> None:
    with _box("🎯 Så läser du Bolag i detalj när du ska köpa", expanded=False):
        st.markdown(
            """
- **Slutsatsrutan** är kärnan: kategori + *därför* + *det här talar emot*. Siffran i blå ruta säger vad **samma läge historiskt betytt för en köpare** (plus-andel, median, typisk topp/dipp, tid till topp).
- **🚫 Ogiltigt om** är ditt **sälj-villkor** — inträffar det är tesen bruten, sälj, oavsett kurs.
- **Tidshorisont** = median tid till toppen för det läget. Den är en *ram* för hur länge du planerar att sitta, inte ett facit.
- **Historiska analoger** = liknande lägen i andra bolag och vad som hände sen. Litet urval → indikation, inte bevis.
- **Uppbyggnadspoäng** (0–100) = hur tydligt bolaget bygger upp tyst; **Redan synligt** = redan uppe vid toppen (inget informationsövertag).
- **Så gör du:** läs slutsats → *Ogiltigt om* → analoger → sätt mål/stop/tid → öva i Paperhandel (knappen högst upp).
"""
        )
        st.caption(CAVEATS)


# -------------------------------------------------------------------- övriga sidor
def alla_bolag_guide() -> None:
    with _box("🎯 Så använder du Alla bolag när du ska köpa", expanded=False):
        st.markdown(
            "**Vad sidan är:** hela listan i en tabell — för att **slå upp och jämföra** bolag, inte för att få köptips. "
            "Sorterad på **Bedömning** (samma band som Market Radar: 🔥/📈 bäst, ⚪ sämst). **Använd:** sök ett bolag du hört talas om, "
            "se dess band, klicka in för full analys. Vill du ha *kandidater* → Market Radar / Dagens upptäckter."
        )


def paper_guide() -> None:
    with _box("🎯 Så använder du Paperhandel", expanded=False):
        st.markdown(
            "Öva med fejkade pengar **innan** riktiga. Skriv ner **mål, stop och tid** före varje köp (från bolagets sida) och jämför sen med "
            "vad som hände — det är så du lär dig om oddsen håller. Kom ihåg: småbolag har oftare slutat på minus än plus; "
            "diversifiera och lita inte på ett enda utfall."
        )


def performance_guide() -> None:
    with _box("🎯 Så använder du Performance", expanded=False):
        st.markdown(
            "Här följs varje sparad upptäckt upp mot vad som faktiskt hände (+1/5/20/30/60/90 dagar). **Det här är beviset över tid**: "
            "håller Noels kandidater bättre än slumpen i verkligheten, eller bara i historiken? Vänta med att lita på verktyget tills här finns "
            "tillräckligt många utfall."
        )


def overview_guide() -> None:
    with _box("🎯 Så använder du Noel när du ska köpa", expanded=False):
        st.markdown(
            "**Arbetsgång:** 1) **Dagens upptäckter** eller **Market Radar** → kandidater · 2) **Bolag i detalj** → slutsats, *Ogiltigt om*, "
            "mål/tid · 3) bestäm mål, stop och tid **innan** köp · 4) öva i **Paperhandel** · 5) följ upp under **Performance**.\n\n"
            "**Ärligt:** i småbolag har de flesta köp historiskt slutat på minus efter 20 dagar. Noel flyttar oddsen (mindre risk, något bättre "
            "träffchans) — det hittar inga garanterade vinnare, och att jaga bolag som redan rusat har *inte* fungerat."
        )
        st.markdown(PAGE_MAP)
