"""Common ingestion contract + the shared write path.

Adapters parse a source into a :class:`RawPriceBatch` (one tidy DataFrame, no
transformation) and hand it to :func:`write_price_batch`, which records an
``ingestion_run`` + ``data_vintage``, dumps the raw rows to ``data/raw/`` as
immutable Parquet, and upserts ``price_daily``.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from typing import Protocol

import duckdb
import pandas as pd

from marc.config import get_logger, get_settings

log = get_logger(__name__)

_PRICE_COLS = ["isin", "session_date", "open", "high", "low", "close", "volume"]


@dataclass
class RawPriceBatch:
    """Tidy, untransformed price rows from one source pull."""

    rows: pd.DataFrame  # isin, session_date, open, high, low, close, volume [, mic, currency, turnover]
    source: str
    pulled_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.UTC))
    params: dict | None = None

    @property
    def stamp(self) -> str:
        return self.pulled_at.strftime("%Y%m%dT%H%M%SZ")

    @property
    def vintage_id(self) -> str:
        return f"{self.source}:{self.stamp}"

    def validate(self) -> None:
        missing = [c for c in _PRICE_COLS if c not in self.rows.columns]
        if missing:
            raise ValueError(f"RawPriceBatch missing columns: {missing}")


class PriceSource(Protocol):
    name: str
    cost: str
    enabled: bool

    def fetch_prices(
        self, securities: pd.DataFrame, start: dt.date, end: dt.date
    ) -> RawPriceBatch: ...


def write_price_batch(con: duckdb.DuckDBPyConnection, batch: RawPriceBatch) -> dict:
    batch.validate()
    settings = get_settings()

    df = batch.rows.copy()
    df["session_date"] = pd.to_datetime(df["session_date"]).dt.date
    for opt in ("mic", "currency", "turnover"):
        if opt not in df.columns:
            df[opt] = pd.NA

    started = dt.datetime.now(dt.UTC)
    con.execute(
        "INSERT INTO ingestion_run (source, started_at, status, n_in) VALUES (?, ?, 'running', ?)",
        [batch.source, started, len(df)],
    )
    run_id = con.execute("SELECT max(run_id) FROM ingestion_run").fetchone()[0]

    raw_dir = settings.raw_dir / batch.source / batch.stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(raw_dir / "prices.parquet", index=False)
    con.execute(
        "INSERT OR REPLACE INTO data_vintage "
        "(vintage_id, source, pulled_at, coverage_start, coverage_end, n_rows, params, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [batch.vintage_id, batch.source, batch.pulled_at, df["session_date"].min(),
         df["session_date"].max(), len(df),
         None if batch.params is None else json.dumps(batch.params), str(raw_dir)],
    )

    sec = con.execute("SELECT isin, security_id, currency AS sec_ccy, base_listing_mic FROM security").df()
    m = df.merge(sec, on="isin", how="left")
    rejected = int(m["security_id"].isna().sum())
    ok = m.dropna(subset=["security_id"]).copy()
    ok["security_id"] = ok["security_id"].astype("int64")
    ok["currency"] = ok["currency"].fillna(ok["sec_ccy"])
    ok["mic"] = ok["mic"].fillna(ok["base_listing_mic"])
    ok["turnover"] = ok["turnover"].fillna(ok["volume"] * ok["close"])
    ok["source"] = batch.source
    ok["vintage_id"] = batch.vintage_id
    ok["event_time"] = pd.to_datetime(ok["session_date"]) + pd.Timedelta(hours=17, minutes=30)

    con.register("ok_df", ok)
    con.execute(
        """
        INSERT OR REPLACE INTO price_daily
        (security_id, session_date, mic, open, high, low, close, volume, turnover,
         currency, is_adjusted, source, vintage_id, event_time, ingested_at)
        SELECT security_id, session_date, mic, open, high, low, close, volume, turnover,
               currency, FALSE, source, vintage_id, event_time, now()
        FROM ok_df
        """
    )
    con.unregister("ok_df")
    con.execute(
        "UPDATE ingestion_run SET finished_at = now(), status = 'ok', n_rejected = ? WHERE run_id = ?",
        [rejected, run_id],
    )
    log.info("ingest %s: %d rows, %d rejected (vintage %s)",
             batch.source, len(ok), rejected, batch.vintage_id)
    return {"run_id": run_id, "vintage_id": batch.vintage_id, "rows": len(ok), "rejected": rejected}
