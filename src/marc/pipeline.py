"""End-to-end v0.1 pipeline: migrate -> seed -> ingest -> clean -> universe ->
panel -> stats (E1) -> signals.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from marc.cleaning import run_cleaning
from marc.config import get_logger, get_settings, universe_config
from marc.db import run_migrations
from marc.db.session import session
from marc.ingestion.attention import SyntheticAttentionSource, write_attention_batch
from marc.ingestion.base import write_price_batch
from marc.ingestion.synthetic_source import SyntheticPriceSource
from marc.ingestion.yfinance_source import YFinancePriceSource
from marc.panel import build_panel
from marc.reference.corporate_actions import load_corporate_actions
from marc.reference.securities import SEED_DIR, load_seed_securities
from marc.reference.universe import build_universe
from marc.signals import apply_rules
from marc.stats import run_experiment_e1

log = get_logger(__name__)


def _reset_db() -> None:
    p = get_settings().abs_db_path
    for suffix in ("", ".wal"):
        f = p.with_name(p.name + suffix) if suffix else p
        if f.exists():
            f.unlink()
    log.info("reset: removed %s", p)


def run_all(source: str = "synthetic", reset: bool = False) -> dict:
    if reset:
        _reset_db()

    ucfg = universe_config()
    ingest_start = (pd.Timestamp(ucfg["study_start"]) - pd.DateOffset(years=2)).date()
    ingest_end = dt.date.today()

    with session(read_only=False) as con:
        run_migrations(con)
        secs = load_seed_securities(con)
        load_corporate_actions(con)

        if source == "synthetic":
            actions = pd.read_csv(SEED_DIR / "corporate_actions.csv")[
                ["isin", "action_type", "ex_date", "ratio"]
            ]
            src: object = SyntheticPriceSource(actions)
        elif source == "yfinance":
            src = YFinancePriceSource()
        else:  # pragma: no cover
            raise ValueError(f"unknown source: {source}")

        batch = src.fetch_prices(secs, ingest_start, ingest_end)
        ingest = write_price_batch(con, batch)
        clean = run_cleaning(con)

        # attention (search / news / forum) — synthetic källa, offline. Riktiga
        # adaptrar (Trends/nyheter/forum) kopplas in som --source senare.
        attn_batch = SyntheticAttentionSource().fetch_attention(secs, ingest_start, ingest_end)
        attn = write_attention_batch(con, attn_batch)

        n_intervals = build_universe(con)
        panel = build_panel(con)
        e1 = run_experiment_e1(con)
        sig = apply_rules(con)

    summary = {
        "source": source,
        "ingest": ingest,
        "attention": attn,
        "cleaning": clean,
        "universe_intervals": n_intervals,
        "panel": panel,
        "e1": e1,
        "signals": sig,
    }
    log.info("pipeline done")
    return summary
