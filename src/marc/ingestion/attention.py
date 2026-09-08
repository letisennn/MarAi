"""Attention-ingestion: search / news / forum -> ``attention_daily``.

Samma mönster som priser: en adapter parsar en källa till en
:class:`RawAttentionBatch` och lämnar den till :func:`write_attention_batch`,
som registrerar ``ingestion_run`` + ``data_vintage``, dumpar rådata till
``data/raw/`` och upsertar ``attention_daily``.

Standardadaptern är :class:`SyntheticAttentionSource` — deterministisk, offline,
INTE riktig data. Riktiga adaptrar (Google Trends, Google News RSS, Reddit) är
stubbar i ``trends_source`` / ``news_source`` / ``forum_source`` tills de kopplas
in som ``--source``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass, field

import duckdb
import numpy as np
import pandas as pd

from marc.config import get_logger, get_settings

log = get_logger(__name__)

_COLS = ["isin", "session_date", "channel", "value", "n_mentions"]
_CHANNELS = ("search", "news", "forum")


@dataclass
class RawAttentionBatch:
    rows: pd.DataFrame          # isin, session_date, channel, value, n_mentions
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
        missing = [c for c in _COLS if c not in self.rows.columns]
        if missing:
            raise ValueError(f"RawAttentionBatch missing columns: {missing}")


def write_attention_batch(con: duckdb.DuckDBPyConnection, batch: RawAttentionBatch) -> dict:
    batch.validate()
    settings = get_settings()
    df = batch.rows.copy()
    if df.empty:
        log.warning("attention %s: empty batch", batch.source)
        return {"rows": 0, "vintage_id": batch.vintage_id}
    df["session_date"] = pd.to_datetime(df["session_date"]).dt.date

    started = dt.datetime.now(dt.UTC)
    con.execute(
        "INSERT INTO ingestion_run (source, started_at, status, n_in) VALUES (?, ?, 'running', ?)",
        [f"attention:{batch.source}", started, len(df)],
    )
    run_id = con.execute("SELECT max(run_id) FROM ingestion_run").fetchone()[0]

    raw_dir = settings.raw_dir / f"attention_{batch.source}" / batch.stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(raw_dir / "attention.parquet", index=False)
    con.execute(
        "INSERT OR REPLACE INTO data_vintage "
        "(vintage_id, source, pulled_at, coverage_start, coverage_end, n_rows, params, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [batch.vintage_id, f"attention:{batch.source}", batch.pulled_at,
         df["session_date"].min(), df["session_date"].max(), len(df),
         None if batch.params is None else json.dumps(batch.params), str(raw_dir)],
    )

    sec = con.execute("SELECT isin, security_id FROM security").df()
    m = df.merge(sec, on="isin", how="left")
    rejected = int(m["security_id"].isna().sum())
    ok = m.dropna(subset=["security_id"]).copy()
    ok["security_id"] = ok["security_id"].astype("int64")
    ok["source"] = batch.source
    ok["vintage_id"] = batch.vintage_id
    ok["event_time"] = pd.to_datetime(ok["session_date"]) + pd.Timedelta(hours=12)

    con.register("attn_df", ok[["security_id", "session_date", "channel", "value",
                                "n_mentions", "source", "vintage_id", "event_time"]])
    con.execute(
        """
        INSERT OR REPLACE INTO attention_daily
        (security_id, session_date, channel, value, n_mentions, source, vintage_id,
         event_time, ingested_at)
        SELECT security_id, session_date, channel, value, n_mentions, source, vintage_id,
               event_time, now()
        FROM attn_df
        """
    )
    con.unregister("attn_df")
    con.execute(
        "UPDATE ingestion_run SET finished_at = now(), status = 'ok', n_rejected = ? WHERE run_id = ?",
        [rejected, run_id],
    )
    log.info("attention %s: %d rows, %d rejected (vintage %s)",
             batch.source, len(ok), rejected, batch.vintage_id)
    return {"run_id": run_id, "vintage_id": batch.vintage_id, "rows": len(ok), "rejected": rejected}


def _seed(isin: str, salt: int) -> int:
    return int.from_bytes(hashlib.sha1(f"{isin}:{salt}".encode()).digest()[:7], "big")


class SyntheticAttentionSource:
    """Deterministisk vecko-attention per ISIN. INTE riktig data.

    Search = ett 0–100-index (Google Trends-likt). News/forum = antal per vecka.
    Serierna har egna sporadiska toppar. De är **inte** medvetet konstruerade att
    leda priset (till skillnad från den syntetiska priskällan som har inbyggt
    momentum) — så deras uppmätta informationsvärde ska bli ~0 tills riktig data
    kopplas in. Poängen är att hela kedjan kör.
    """

    name = "synthetic"
    cost = "free"
    enabled = True

    def _one(self, isin: str, weeks: pd.DatetimeIndex) -> pd.DataFrame:
        rng = np.random.default_rng(_seed(isin, 991))
        n = len(weeks)
        if n < 8:
            return pd.DataFrame()

        # gemensam "uppmärksamhetsprofil" per bolag
        base_search = rng.uniform(8, 45)
        pop = rng.uniform(0.2, 3.0)          # hur mycket folk pratar om bolaget alls

        # AR(1)-brus
        def ar1(sd: float) -> np.ndarray:
            e = rng.normal(0, sd, n)
            x = np.zeros(n)
            for i in range(1, n):
                x[i] = 0.75 * x[i - 1] + e[i]
            return x

        search = base_search + base_search * 0.35 * ar1(1.0)
        forum = np.clip(pop * (2.0 + ar1(0.8)), 0, None)
        news = np.clip(pop * (0.6 + 0.5 * ar1(0.6)), 0, None)

        # 2–4 gemensamma toppfönster
        for _ in range(int(rng.integers(2, 5))):
            s = int(rng.integers(4, max(5, n - 6)))
            length = int(rng.integers(2, 6))
            e = min(n, s + length)
            mult = rng.uniform(1.8, 4.5)
            search[s:e] *= mult
            forum[s:e] *= mult * rng.uniform(0.7, 1.4)
            news[s:e] *= mult * rng.uniform(0.5, 1.2)

        search = np.clip(search, 0, 100)
        rows = []
        for ch, arr, is_count in (("search", search, False), ("news", news, True), ("forum", forum, True)):
            vals = np.round(arr, 2)
            cnt = np.round(arr).astype("int64") if is_count else pd.array([pd.NA] * n, dtype="Int64")
            rows.append(pd.DataFrame({
                "isin": isin, "session_date": weeks.date, "channel": ch,
                "value": vals, "n_mentions": cnt,
            }))
        return pd.concat(rows, ignore_index=True)

    def fetch_attention(self, securities: pd.DataFrame, start: dt.date, end: dt.date) -> RawAttentionBatch:
        weeks = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="W-FRI")
        frames = [self._one(row["isin"], weeks) for _, row in securities.iterrows()]
        frames = [f for f in frames if not f.empty]
        rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=_COLS)
        log.info("synthetic attention: %d rows for %d securities", len(rows), len(frames))
        return RawAttentionBatch(rows=rows, source=self.name,
                                 params={"start": str(start), "end": str(end), "channels": list(_CHANNELS)})
