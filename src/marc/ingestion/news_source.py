"""Nyhetsflödes-adapter — riktiga rubriker via Google News RSS.

Godkänd källa (Jonas 2026-09-08). Räknar rubriker per bolag och vecka +
en enkel, regelbaserad sentimentpoäng (positiva minus negativa svenska
finansord i rubriktexten, normaliserat -1..1) — INGEN LLM (CLAUDE.md regel 4,
gäller till v0.5). Sentimentordlistan är grov med flit; se den som en
riktningsindikation, inte en tolkning.

**Känd begränsning (viktig):** Google News RSS-sökning ger bara ett
NUVARANDE fönster av träffar (typiskt de senaste veckorna/månaderna), ingen
djup historisk arkiv-API. Till skillnad från Trends (som ger hela 5-års-
fönstret på en gång) byggs riktigt nyhetsdjup därför upp GRADVIS över
kalendertid, en körning i taget (``write_attention_batch`` upsertar, skriver
inte över gamla veckor). En ``--reset`` av databasen nollställer det byggda
djupet. Feature-funktionerna (``features/attention.py``) hanterar glesa/
saknade veckor genom att returnera NaN tills tillräckligt fönster finns —
ingen krasch, bara "inte tillräckligt än".

**ToS-notis (regel 11):** RSS-flödets copyright-text anger "personal,
non-commercial use ... within a personal feed reader". Det här är ett
privat, icke-kommersiellt tvåpersoners forskningsverktyg som bara aggregerar
räkning + enkel nyckelordsstatistik (republicerar inte artikeltext) — men
notisen är strikt formulerad och läggs upp här i sin helhet så att
avvägningen är synlig, inte gömd.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

import pandas as pd
import requests

from marc.config import get_logger
from marc.ingestion.attention import RawAttentionBatch

log = get_logger(__name__)

_PACE_SECONDS = 0.8
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NoelAI-internal-research/0.1)"}

_POS_WORDS = [
    "rusar", "rekordvinst", "rekordresultat", "vinstlyft", "överträffar",
    "höjer prognosen", "höjer riktkursen", "stororder", "stororder",
    "vinner order", "tecknar avtal", "uppgraderar", "höjd rekommendation",
    "stark tillväxt", "ökar vinsten", "expanderar", "genombrott", "godkänt",
    "godkänner", "förvärvar", "rekordorder", "överträffade", "vinstvarning i positiv riktning",
]
_NEG_WORDS = [
    "rasar", "vinstvarning", "nedgraderar", "sänker prognosen", "sänker riktkursen",
    "missar förväntningarna", "förlust", "konkurs", "nyemission", "utspädning",
    "avnoteras", "handelsstopp", "utreds", "bötfälls", "stämning", "vd lämnar",
    "vd avgår", "varsel", "nedskrivning", "svag försäljning", "tappar", "sjunker",
    "rekonstruktion",
]


def _keyword_sentiment(titles: list[str]) -> float | None:
    if not titles:
        return None
    pos = neg = 0
    for t in titles:
        tl = t.lower()
        pos += sum(1 for w in _POS_WORDS if w in tl)
        neg += sum(1 for w in _NEG_WORDS if w in tl)
    total = pos + neg
    return 0.0 if total == 0 else (pos - neg) / total


def fetch_headlines_for(name: str) -> list[tuple[dt.datetime, str]]:
    """Rubriker + publiceringstid för ett bolagsnamn, direkt från Google News RSS.
    Delas av :meth:`NewsSource.fetch_attention` och LLM-narrativmodulen
    (``marc.llm.narrative``), som hämtar färskt på begäran i stället för att
    spara rå rubriktext permanent."""
    url = f"https://news.google.com/rss/search?q={quote(name)}&hl=sv-SE&gl=SE&ceid=SE:sv"
    r = requests.get(url, timeout=15, headers=_HEADERS)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    items: list[tuple[dt.datetime, str]] = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        pub = item.findtext("pubDate")
        if not pub:
            continue
        try:
            d = email.utils.parsedate_to_datetime(pub)
        except (TypeError, ValueError):
            continue
        items.append((d, title))
    return items


class NewsSource:
    name = "googlenews-rss"
    cost = "free"
    enabled = True

    def fetch_attention(
        self, securities: pd.DataFrame, start: dt.date, end: dt.date
    ) -> RawAttentionBatch:
        have = securities.dropna(subset=["name"])
        rows: list[dict] = []
        ok_n = 0
        for i, (_, sec) in enumerate(have.iterrows()):
            name = str(sec["name"])
            try:
                items = fetch_headlines_for(name)
            except Exception as exc:  # noqa: BLE001 - nät/parsing, en trasig källa ska inte stoppa hela pullen
                log.warning("news rss %s failed: %s", name, exc)
                time.sleep(_PACE_SECONDS)
                continue

            if items:
                ok_n += 1
                idf = pd.DataFrame(items, columns=["dt", "title"])
                idf["dt"] = pd.to_datetime(idf["dt"], utc=True).dt.tz_localize(None)
                idf["week"] = idf["dt"].dt.to_period("W-FRI").dt.end_time.dt.normalize()
                for wk, grp in idf.groupby("week"):
                    n = len(grp)
                    rows.append({
                        "isin": sec["isin"], "session_date": wk.date(),
                        "value": float(n), "n_mentions": int(n),
                        "sentiment": _keyword_sentiment(grp["title"].tolist()),
                    })
            if (i + 1) % 50 == 0:
                log.info("news rss: %d/%d bolag klara", i + 1, len(have))
            time.sleep(_PACE_SECONDS)

        out = pd.DataFrame(rows, columns=["isin", "session_date", "value", "n_mentions", "sentiment"])
        out["channel"] = "news"
        log.info("news rss: %d rader för %d/%d bolag (nyhetsträffar)", len(out), ok_n, len(have))
        return RawAttentionBatch(
            rows=out[["isin", "session_date", "channel", "value", "n_mentions", "sentiment"]],
            source=self.name, params={"lang": "sv-SE", "geo": "SE"},
        )
