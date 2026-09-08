"""Forum/social-adapter (stub).

Räknar inlägg/kommentarer per bolag och vecka + unika/nya deltagare. Planerad
källa: Reddit officiella API (r/aktier m.fl.). Godkänd (Jonas 2026-09-08).
Nordiska forum (Placera/Shareville/Di.se) kräver ToS-kontroll per källa (regel 11)
— scrapa inte där det är förbjudet. GDPR: hasha user-id, bestäm retention.
Fyller ``attention_daily`` kanal ``forum``.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from marc.ingestion.attention import RawAttentionBatch


class ForumSource:
    name = "reddit"
    cost = "free"
    enabled = False

    def fetch_attention(
        self, securities: pd.DataFrame, start: dt.date, end: dt.date
    ) -> RawAttentionBatch:  # pragma: no cover - stub
        raise NotImplementedError(
            "ForumSource är en stub. Kräver: Reddit app-credentials, sökning per "
            "bolag/ticker, veckoaggregering, hashade user-id för unika/nya deltagare."
        )
