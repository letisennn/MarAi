#!/usr/bin/env python
"""Regenerate ``data/seed/securities.csv`` from Yahoo Finance's own screener.

Not part of ``marc pipeline`` — run manually when the seed list needs
refreshing (rule 9: reproducible, so it lives here instead of a one-off
scratch script). Uses ``yfinance.screen`` / ``EquityQuery`` — the same,
already-documented Yahoo source as price ingestion (see
``docs/data_sources.md``), not a new external source and no scraping of
third-party sites.

Filters out ETFs/ETNs/leveraged certificates that Yahoo mistags as EQUITY,
subscription-right/BTA instruments, and anything above ``--max-market-cap``
(default 10bn SEK — comfortably above the small/mid-cap ceiling in
``config/universe.yml``, so genuine large caps are skipped without touching
the config's own admission logic).

Usage:
    uv run python scripts/generate_seed_universe.py [--max-market-cap 10e9] [--out data/seed/securities.csv]
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path

BAD_NAME = re.compile(
    r"xtrackers|ucits|\betf\b|\betn\b|tracker|certifikat|\bbull\b|\bbear\b|"
    r"mini l|mini s|warrant|\bunit(s)?\b",
    re.I,
)
BAD_TICKER = re.compile(r"-(BTA|TR|RT|RTS|TO|UNIT|XBT|XBTE|VALOU)(\.ST)?$")


def fetch_all_se_quotes() -> list[dict]:
    import yfinance as yf

    q = yf.EquityQuery("eq", ["region", "se"])
    out: list[dict] = []
    offset, size = 0, 250
    while True:
        res = yf.screen(q, size=size, offset=offset)
        quotes = res.get("quotes", [])
        out.extend(quotes)
        total = res.get("total", 0)
        offset += size
        if offset >= total or not quotes:
            break
        time.sleep(0.5)
    return out


def build_rows(quotes: list[dict], max_market_cap: float) -> list[dict]:
    rows, seen = [], set()
    for x in quotes:
        sym = x.get("symbol") or ""
        if not sym.endswith(".ST") or x.get("currency") != "SEK":
            continue
        mc, sh = x.get("marketCap"), x.get("sharesOutstanding")
        if not mc or not sh or mc <= 0 or sh <= 0 or mc > max_market_cap:
            continue
        name = (x.get("longName") or x.get("shortName") or "").strip()
        if not name or BAD_NAME.search(name) or BAD_TICKER.search(sym):
            continue
        if sym.startswith(("BULL-", "BEAR-")) or sym in seen:
            continue
        seen.add(sym)
        rows.append({
            "isin": sym, "name": name.replace(" (publ)", "").strip(),
            "country": "SE", "currency": "SEK", "mic": "XSTO", "market_segment": "main",
            "yahoo": sym, "sector": "", "shares_out_millions": round(sh / 1e6, 4),
            "list_date": "2015-01-01", "status": "listed", "status_date": "", "status_detail": "",
        })
    rows.sort(key=lambda r: r["name"])
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-market-cap", type=float, default=10_000_000_000)
    ap.add_argument("--out", default="data/seed/securities.csv")
    args = ap.parse_args()

    quotes = fetch_all_se_quotes()
    rows = build_rows(quotes, args.max_market_cap)
    print(f"{len(quotes)} raw quotes -> {len(rows)} candidates "
          f"(currency=SEK, market cap <= {args.max_market_cap:,.0f} SEK, junk filtered)")

    out = Path(args.out)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
