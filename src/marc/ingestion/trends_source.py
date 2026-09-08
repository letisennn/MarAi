"""Google Trends-adapter (stub).

Riktig sökintresse-data via ``pytrends``. Inte inkopplad än — kräver
term-mappning per bolag och stitching av Trends omnormalisering mellan pulls.
Godkänd källa (Jonas 2026-09-08); implementera när den ska köras som ``--source``.
Fyller ``attention_daily`` kanal ``search`` via
:func:`marc.ingestion.attention.write_attention_batch`.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from marc.ingestion.attention import RawAttentionBatch


class TrendsSource:
    name = "pytrends"
    cost = "free"
    enabled = False

    def fetch_attention(
        self, securities: pd.DataFrame, start: dt.date, end: dt.date
    ) -> RawAttentionBatch:  # pragma: no cover - stub
        raise NotImplementedError(
            "TrendsSource är en stub. Kräver: config/attention_terms.yml (bolag -> sökord), "
            "pytrends-anrop i 5-års-fönster, normaliserings-stitching, backoff mot rate-limit."
        )
