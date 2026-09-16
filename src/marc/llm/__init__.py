"""LLM analysis.

**Undantag 2026-09-16 (Jonas)**: `narrative.py` är i bruk före v0.5 ("Gör
undantag nu" på uttrycklig fråga) — nyanserad sentiment/narrativklassificering
av nyhetsrubriker via Claude, ett bolag i taget, på begäran. Kärnregeln i
CLAUDE.md regel 4 gäller ändå: modellen hanterar bara ostrukturerad text och
får ALDRIG hitta på ett kvantitativt påstående (sannolikhet, riktkurs,
prognos) — bara klassificera vad texten faktiskt säger. Siffror i appen
kommer alltid från databasen/statistiklagret.

Allt annat LLM-arbete (catalyst-klassificering, forum-sammanfattning,
earnings-call-tonanalys, jämförande narrativ över tid) är fortfarande
DEFERRED till v0.5 och kräver eget sign-off.
"""

from marc.llm.narrative import NarrativeResult, classify_narrative, classify_narrative_for_company

__all__ = ["NarrativeResult", "classify_narrative", "classify_narrative_for_company"]
