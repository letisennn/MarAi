"""Nyhetsflödes-adapter (stub).

Räknar nyhetsrubriker per bolag och vecka + enkel ton (nyckelord, ingen LLM före
v0.5). Planerade källor: Google News RSS per bolagsnamn, GDELT 2.0. Godkänd
(Jonas 2026-09-08). Fyller ``attention_daily`` kanal ``news``.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from marc.ingestion.attention import RawAttentionBatch


class NewsSource:
    name = "googlenews-rss"
    cost = "free"
    enabled = False

    def fetch_attention(
        self, securities: pd.DataFrame, start: dt.date, end: dt.date
    ) -> RawAttentionBatch:  # pragma: no cover - stub
        raise NotImplementedError(
            "NewsSource är en stub. Kräver: RSS-hämtning per bolagsnamn/ISIN, dedup, "
            "veckoaggregering, ev. enkel nyckelordston. GDELT som alternativ backbone."
        )
