"""Synthetic price source — the default for v0.1.

Deterministic pseudo-random OHLCV per ISIN so the whole pipeline and the web app
run offline and reproducibly. It honours seeded corporate actions (splits make
the *raw* price jump, so the adjustment code path is exercised) and listing
status (bankruptcies crash toward zero, acquisitions converge to the offer
price). It is NOT market data — it exists to exercise and demo the system.
"""

from __future__ import annotations

import datetime as dt
import hashlib

import numpy as np
import pandas as pd

from marc.config import get_logger
from marc.ingestion.base import RawPriceBatch

log = get_logger(__name__)


def _seed(isin: str) -> int:
    return int.from_bytes(hashlib.sha1(isin.encode()).digest()[:7], "big")


class SyntheticPriceSource:
    name = "synthetic"
    cost = "free"
    enabled = True

    def __init__(self, actions: pd.DataFrame | None = None) -> None:
        # actions: isin, action_type, ex_date, ratio
        self.actions = actions if actions is not None else pd.DataFrame(
            columns=["isin", "action_type", "ex_date", "ratio"]
        )

    def _splits_for(self, isin: str) -> list[tuple[dt.date, float]]:
        a = self.actions
        if a.empty:
            return []
        rows = a[(a["isin"] == isin) & (a["action_type"] == "split")]
        return [(pd.to_datetime(d).date(), float(r)) for d, r in zip(rows["ex_date"], rows["ratio"])]

    def _one(self, sec: pd.Series, start: dt.date, end: dt.date) -> pd.DataFrame:
        rng = np.random.default_rng(_seed(sec["isin"]))

        list_date = pd.to_datetime(sec.get("list_date")).date() if pd.notna(sec.get("list_date")) else start
        begin = max(start, list_date)
        status = str(sec.get("status") or "listed")
        status_date = pd.to_datetime(sec.get("status_date")).date() if pd.notna(sec.get("status_date")) else None
        stop = min(end, status_date) if status_date and status in {"delisted", "acquired", "bankrupt"} else end
        if stop <= begin:
            return pd.DataFrame()

        dates = pd.bdate_range(begin, stop)
        n = len(dates)
        if n < 30:
            return pd.DataFrame()

        # low mean drift with wide cross-sectional dispersion (incl. negatives),
        # so market caps do not all compound past the small-cap ceiling.
        mu_d = rng.normal(0.01, 0.16) / 252.0
        sig_d = rng.uniform(0.22, 0.55) / np.sqrt(252.0)
        logret = rng.normal(mu_d, sig_d, n)
        jump_mask = rng.random(n) < 0.008
        logret[jump_mask] += rng.normal(0.0, 0.10, int(jump_mask.sum()))

        # episodic "attention bursts": a few windows of extra drift + heavy volume
        vol_mult = np.ones(n)
        for _ in range(rng.integers(2, 5)):
            if n < 60:
                break
            s = int(rng.integers(30, n - 25))
            length = int(rng.integers(10, 26))
            e = min(n, s + length)
            logret[s:e] += rng.normal(0.0012, 0.001)
            vol_mult[s:e] *= rng.uniform(1.8, 4.0)

        # Decouple price level, market cap and turnover so each is well spread:
        # draw a target market cap and a target daily turnover, back out the
        # local price level and the share-volume base from them.
        fx_guess = {"SEK": 1.0, "NOK": 0.98, "DKK": 1.52, "EUR": 11.35}.get(sec.get("currency", "SEK"), 1.0)
        shares = max(float(sec.get("shares_out_millions", 20)) * 1e6, 1.0)
        mc0_sek = 10.0 ** rng.uniform(np.log10(1.5e8), np.log10(2.2e9))     # ~150M..2.2bn SEK
        p0_local = mc0_sek / (shares * fx_guess)
        close = p0_local * np.exp(np.cumsum(logret))

        turnover0_sek = 10.0 ** rng.uniform(np.log10(4.0e5), np.log10(6.0e7))  # ~0.4M..60M SEK/day
        vol_base = turnover0_sek / max(p0_local * fx_guess, 1e-6)
        vol = (
            vol_base
            * np.exp(rng.normal(0.0, 0.55, n))
            * (1.0 + 3.0 * np.abs(logret) / sig_d)
            * vol_mult
        )

        # splits: raw price divided by ratio from ex_date onward; volume multiplied
        idx = pd.DatetimeIndex(dates)
        for ex_date, ratio in self._splits_for(sec["isin"]):
            mask = idx.date >= ex_date
            close[mask] /= ratio
            vol[mask] *= ratio

        # listing-status tail
        if status == "bankrupt":
            k = min(20, n // 3)
            decay = np.linspace(0.0, 1.0, k) ** 2
            close[-k:] *= (1.0 - 0.985 * decay)
            vol[-k:] *= np.linspace(4.0, 0.2, k)
        elif status == "acquired":
            offer = sec.get("status_detail")
            offer = float(offer) if pd.notna(offer) else float(close[-1])
            k = min(12, n // 4)
            w = np.linspace(0.0, 1.0, k)
            close[-k:] = close[-k:] * (1.0 - w) + offer * w
            vol[-k:] *= np.linspace(2.5, 0.6, k)

        prev = np.concatenate([[close[0]], close[:-1]])
        gap = rng.normal(0.0, 0.004, n)
        open_ = prev * (1.0 + gap)
        tr = sig_d * rng.uniform(0.4, 2.2, n)
        hi = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.0, tr)))
        lo = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.0, tr)))
        lo = np.maximum(lo, 0.01)

        return pd.DataFrame(
            {
                "isin": sec["isin"],
                "session_date": idx.date,
                "open": np.round(open_, 4),
                "high": np.round(hi, 4),
                "low": np.round(lo, 4),
                "close": np.round(close, 4),
                "volume": np.round(np.maximum(vol, 1.0)).astype("int64"),
                "currency": sec.get("currency", "SEK"),
                "mic": sec.get("mic"),
            }
        )

    def fetch_prices(self, securities: pd.DataFrame, start: dt.date, end: dt.date) -> RawPriceBatch:
        frames = [self._one(row, start, end) for _, row in securities.iterrows()]
        frames = [f for f in frames if not f.empty]
        rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
            columns=["isin", "session_date", "open", "high", "low", "close", "volume", "currency", "mic"]
        )
        log.info("synthetic: generated %d rows for %d securities", len(rows), len(frames))
        return RawPriceBatch(rows=rows, source=self.name, params={"start": str(start), "end": str(end)})
