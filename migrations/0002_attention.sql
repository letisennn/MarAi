-- 0002: attention data (search / news / forum) — one channel-keyed table.
--
-- Roadmap v0.2–0.4, tidigarelagt 2026-09-08 (Jonas). Weekly cadence. Synthetic
-- source first (offline, deterministisk) precis som priser; riktiga adaptrar
-- (Google Trends, Google News RSS, Reddit) kopplas in som --source senare.
-- Rådumpar skrivs oförändrade till data/raw/ och registreras via data_vintage.

CREATE TABLE attention_daily (
    security_id  BIGINT NOT NULL REFERENCES security(security_id),
    session_date DATE   NOT NULL,        -- veckans fredag
    channel      TEXT   NOT NULL CHECK (channel IN ('search','news','forum')),
    value        DOUBLE,                 -- search: 0..100 index · news/forum: antal per vecka
    n_mentions   BIGINT,                 -- råantal omnämnanden (news/forum); NULL för search
    source       TEXT   NOT NULL,
    vintage_id   TEXT,
    event_time   TIMESTAMP,              -- när det var känt (UTC)
    ingested_at  TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (security_id, session_date, channel, source)
);
