"""Google Trends-adapter — riktig sökintresse-data via ``pytrends``.

Godkänd källa (Jonas 2026-09-08). En pull per bolag över hela studiefönstret
(``today 5-y``) i stället för flera ihopfogade pulls — undviker Google Trends
omnormalisering mellan separata pulls (varje pulls 0–100-skala är relativ till
just det fönstret). Sökordet är bolagsnamnet; ingen ticker-mappning ännu.

Inofficiellt API (ingen nyckel, inget kontrakt) — rate-limitad och kan brytas av
Google när som helst. Körs som ett eget, långsamt steg (``--attention-source
real``), inte del av standardkörningen. ~0.5–1 s/bolag + paus = flera minuter
för hela universumet.
"""

from __future__ import annotations

import datetime as dt
import time

import pandas as pd

from marc.config import get_logger
from marc.ingestion.attention import RawAttentionBatch

log = get_logger(__name__)

_PACE_SECONDS = 1.2
_MAX_RETRIES = 3


class TrendsSource:
    name = "pytrends"
    cost = "free"
    enabled = True

    def fetch_attention(
        self, securities: pd.DataFrame, start: dt.date, end: dt.date
    ) -> RawAttentionBatch:
        from pytrends.request import TrendReq

        pt = TrendReq(hl="sv-SE", tz=60, timeout=(5, 20))
        have = securities.dropna(subset=["name"])
        rows: list[dict] = []
        ok_n = 0
        for i, (_, sec) in enumerate(have.iterrows()):
            kw = str(sec["name"])
            df = None
            for attempt in range(_MAX_RETRIES):
                try:
                    pt.build_payload([kw], timeframe="today 5-y", geo="SE")
                    df = pt.interest_over_time()
                    break
                except Exception as exc:  # noqa: BLE001 - obetalt/inofficiellt API
                    log.warning("pytrends %s attempt %d failed: %s", kw, attempt + 1, exc)
                    time.sleep(3.0 * (attempt + 1))
            if df is None or df.empty or kw not in df.columns:
                time.sleep(_PACE_SECONDS)
                continue
            ok_n += 1
            for d, val in df[kw].items():
                rows.append({
                    "isin": sec["isin"], "session_date": pd.Timestamp(d).date(),
                    "value": float(val), "n_mentions": None,
                })
            if (i + 1) % 50 == 0:
                log.info("pytrends: %d/%d bolag klara", i + 1, len(have))
            time.sleep(_PACE_SECONDS)

        out = pd.DataFrame(rows, columns=["isin", "session_date", "value", "n_mentions"])
        out["channel"] = "search"
        log.info("pytrends: %d rader för %d/%d bolag", len(out), ok_n, len(have))
        return RawAttentionBatch(
            rows=out[["isin", "session_date", "channel", "value", "n_mentions"]],
            source=self.name, params={"timeframe": "today 5-y", "geo": "SE"},
        )
