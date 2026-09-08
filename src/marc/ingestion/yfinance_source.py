"""yfinance adapter — optional real price source (opt-in).

Pulls UNADJUSTED daily OHLCV (``auto_adjust=False``); adjustments are derived
later in :mod:`marc.cleaning`. Unofficial, rate-limited, no SLA, and delisted
tickers are dropped (survivorship bias) — see ``docs/data_sources.md``. The
synthetic source is the default; use this only for spot checks.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from marc.config import get_logger
from marc.ingestion.base import RawPriceBatch

log = get_logger(__name__)


class YFinancePriceSource:
    name = "yfinance"
    cost = "free"
    enabled = True

    def fetch_prices(self, securities: pd.DataFrame, start: dt.date, end: dt.date) -> RawPriceBatch:
        import yfinance as yf  # local import: optional dependency at call time

        out = []
        have_ticker = securities.dropna(subset=["yahoo"])
        for _, sec in have_ticker.iterrows():
            tkr = str(sec["yahoo"])
            try:
                raw = yf.download(
                    tkr, start=str(start), end=str(end),
                    auto_adjust=False, progress=False, threads=False,
                )
            except Exception as exc:  # noqa: BLE001 - third-party, network
                log.warning("yfinance %s failed: %s", tkr, exc)
                continue
            if raw is None or raw.empty:
                log.warning("yfinance %s: no data", tkr)
                continue
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            raw = raw.rename(columns=str.lower).reset_index()
            raw["isin"] = sec["isin"]
            raw["currency"] = sec.get("currency")
            raw["mic"] = sec.get("mic")
            raw = raw.rename(columns={"date": "session_date"})
            out.append(raw[["isin", "session_date", "open", "high", "low", "close", "volume", "currency", "mic"]])

        rows = pd.concat(out, ignore_index=True) if out else pd.DataFrame(
            columns=["isin", "session_date", "open", "high", "low", "close", "volume", "currency", "mic"]
        )
        log.info("yfinance: %d rows for %d/%d tickers", len(rows), len(out), len(have_ticker))
        return RawPriceBatch(rows=rows, source=self.name, params={"start": str(start), "end": str(end)})
