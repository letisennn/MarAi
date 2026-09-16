"""LLM-baserad narrativ-/sentimentklassificering av nyhetsrubriker.

**Undantag från CLAUDE.md regel 4** (Jonas, 2026-09-16: "Gör undantag nu" på
frågan om att börja använda LLM för nyanserad sentiment/narrativ före v0.5).
Kärnbegränsningen i regel 4 gäller ändå OFÖRÄNDRAT: modellen hanterar bara
ostrukturerad text (rubriker) och får ALDRIG hitta på ett kvantitativt
påstående — ingen sannolikhet, riktkurs eller prognos. Bara en klassificering
av vad texten faktiskt säger. Alla siffror i appen kommer från databasen och
statistiklagret, aldrig från modellen.

Kräver ``ANTHROPIC_API_KEY`` i miljön (``.env``). Kostar riktiga pengar per
anrop — litet per körning, men proportionellt mot hur ofta det körs, till
skillnad från en fast månadsprenumeration. Inte del av standardpipelinen:
körs på begäran, ett bolag i taget (``marc llm narrative "<bolagsnamn>"``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from marc.config import get_logger

log = get_logger(__name__)

MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """Du klassificerar svenska finansnyhetsrubriker om ett bolag.

Basera dig ENDAST på rubrikerna som ges nedan — hitta aldrig på fakta som inte
står där. Ge ALDRIG en sannolikhet, riktkurs, vinstprognos eller någon annan
kvantitativ uppskattning om framtiden — bara en sammanfattning av vad
rubrikerna faktiskt säger just nu.

Svara ENDAST med JSON, exakt på den här formen och inget annat:
{"sentiment_label": "starkt negativ|negativ|neutral|positiv|starkt positiv",
 "sentiment_score": <tal mellan -1.0 och 1.0>,
 "theme": "<kort tema, max 6 ord>",
 "reasoning": "<en mening om varför, på svenska>"}"""


@dataclass
class NarrativeResult:
    sentiment_label: str
    sentiment_score: float
    theme: str
    reasoning: str
    model: str
    n_headlines: int


def _require_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY saknas. Lägg till den i .env för att använda LLM-narrativ. "
            "Kostar riktiga pengar per anrop (litet, per token) — se docs/data_sources.md."
        )
    return key


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"kunde inte tolka LLM-svaret som JSON: {text[:200]!r}") from exc


def classify_narrative(company_name: str, headlines: list[str]) -> NarrativeResult:
    """Klassificera en lista rubriker för ett bolag. Rent textklassificerings-
    anrop — inga kvantitativa påståenden begärs eller accepteras från modellen."""
    if not headlines:
        raise ValueError("inga rubriker att klassificera")
    api_key = _require_api_key()

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    user_content = f"Bolag: {company_name}\n\nRubriker (senaste):\n" + "\n".join(
        f"- {h}" for h in headlines[:30]
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    data = _parse_json(text)
    result = NarrativeResult(
        sentiment_label=str(data.get("sentiment_label", "neutral")),
        sentiment_score=max(-1.0, min(1.0, float(data.get("sentiment_score", 0.0)))),
        theme=str(data.get("theme", ""))[:200],
        reasoning=str(data.get("reasoning", ""))[:500],
        model=MODEL,
        n_headlines=len(headlines),
    )
    log.info("llm narrative %s: %s (%s)", company_name, result.sentiment_label, result.theme)
    return result


def classify_narrative_for_company(company_name: str, days: int = 21) -> NarrativeResult:
    """Hämtar färska rubriker via Google News RSS och klassificerar dem.
    Nätanrop + LLM-anrop — kör bara på begäran, inte i batch över hela universumet."""
    import datetime as dt

    from marc.ingestion.news_source import fetch_headlines_for

    items = fetch_headlines_for(company_name)
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=days)
    recent = [title for d, title in items if d >= cutoff or d.tzinfo is None]
    if not recent:
        recent = [title for _, title in items[:15]]  # fallback: ta det som finns
    if not recent:
        raise ValueError(f"inga nyhetsrubriker hittades för {company_name!r}")
    return classify_narrative(company_name, recent)
