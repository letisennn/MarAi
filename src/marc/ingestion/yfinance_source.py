"""yfinance adapter — real daily price source.

Pulls UNADJUSTED daily OHLCV (``auto_adjust=False``); adjustments are derived
later in :mod:`marc.cleaning`. Unofficial and rate-limited, no SLA. Delisted
tickers that Yahoo has dropped return no rows (survivorship bias) — see
``docs/data_sources.md``. Downloads are batched (``group_by="ticker"``) to keep
the number of HTTP calls low.
"""

from __future__ import annotations

import datetime as dt
import time

import pandas as pd

from marc.config import get_logger
from marc.ingestion.base import RawPriceBatch

log = get_logger(__name__)

_BATCH = 25
_COLS = ["isin", "session_date", "open", "high", "low", "close", "volume", "currency", "mic"]


class YFinancePriceSource:
    name = "yfinance"
    cost = "free"
    enabled = True

    def fetch_prices(self, securities: pd.DataFrame, start: dt.date, end: dt.date) -> RawPriceBatch:
        import yfinance as yf  # local import: optional dependency at call time

        have_ticker = securities.dropna(subset=["yahoo"]).copy()
        have_ticker["yahoo"] = have_ticker["yahoo"].astype(str)
        by_ticker = {r["yahoo"]: r for _, r in have_ticker.iterrows()}
        tickers = list(by_ticker)

        out: list[pd.DataFrame] = []
        got: set[str] = set()

        def _pull(chunk: list[str]) -> None:
            try:
                raw = yf.download(
                    chunk, start=str(start), end=str(end),
                    auto_adjust=False, progress=False, threads=True,
                    group_by="ticker",
                )
            except Exception as exc:  # noqa: BLE001 - third-party, network
                log.warning("yfinance batch %s failed: %s", chunk[:3], exc)
                return
            if raw is None or raw.empty:
                log.warning("yfinance batch %s...: no data", chunk[:3])
                return

            for tkr in chunk:
                try:
                    sub = raw[tkr] if len(chunk) > 1 else raw
                except KeyError:
                    continue
                sub = sub.dropna(how="all")
                if sub.empty:
                    log.warning("yfinance %s: no data", tkr)
                    continue
                if isinstance(sub.columns, pd.MultiIndex):
                    sub.columns = sub.columns.get_level_values(-1)
                sub = sub.reset_index()
                sub.columns = [str(c).lower() for c in sub.columns]
                sec = by_ticker[tkr]
                sub["isin"] = sec["isin"]
                sub["currency"] = sec.get("currency")
                sub["mic"] = sec.get("mic")
                sub = sub.rename(columns={"date": "session_date", "index": "session_date"})
                if not {"open", "high", "low", "close", "volume"}.issubset(sub.columns):
                    log.warning("yfinance %s: unexpected columns %s", tkr, list(sub.columns))
                    continue
                out.append(sub[_COLS])
                got.add(tkr)

        for i in range(0, len(tickers), _BATCH):
            _pull(tickers[i : i + _BATCH])
            time.sleep(1.0)  # be polite between batches

        # Yahoo tappar ibland ett helt gäng tickers tillfälligt ("possibly delisted")
        # trots att de finns — 2026-09-23 föll 67 av 671 bort en körning och kom
        # tillbaka nästa. Ta om de saknade i mindre omgångar innan vi ger upp.
        for attempt in range(2):
            missing = [t for t in tickers if t not in got]
            if not missing:
                break
            log.info("yfinance retry %d: %d tickers saknas, försöker igen", attempt + 1, len(missing))
            time.sleep(10.0)
            for i in range(0, len(missing), 8):
                _pull(missing[i : i + 8])
                time.sleep(2.0)

        rows = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=_COLS)
        rows = rows.dropna(subset=["close"])
        log.info("yfinance: %d rows for %d/%d tickers", len(rows), rows["isin"].nunique() if len(rows) else 0, len(tickers))
        return RawPriceBatch(rows=rows, source=self.name, params={"start": str(start), "end": str(end)})
