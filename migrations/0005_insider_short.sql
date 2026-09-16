-- 0005: insiderhandel (FI:s PDMR-register) + blankning (FI:s blankningsregister).
--
-- Godkänt 2026-09-16 (Jonas, uttryckligt "Ja, koppla in båda" på fråga om nya
-- källor utöver regel 3). Båda är gratis, officiella, öppna svenska register
-- (FI kräver bara källhänvisning, ingen annan begränsning). FI publicerar dem
-- via sökportaler (marknadssok.fi.se) utan en dokumenterad bulk-API — data
-- laddas ner manuellt som Excel/CSV via portalens exportfunktion och
-- ingesteras med `marc ingest insider <fil>` / `marc ingest short-interest
-- <fil>`. Se docs/data_sources.md.

CREATE TABLE insider_transaction (
    security_id       BIGINT NOT NULL REFERENCES security(security_id),
    person_name       TEXT,
    role              TEXT,             -- t.ex. "VD", "Styrelseledamot", "Närstående"
    transaction_date  DATE   NOT NULL,
    publication_date  DATE,
    instrument_type   TEXT,
    transaction_type  TEXT   NOT NULL CHECK (transaction_type IN ('buy', 'sell', 'other')),
    volume            DOUBLE,
    price             DOUBLE,
    currency          TEXT,
    amount_sek        DOUBLE,           -- volume * price, riksbank-konverterat vid behov
    source            TEXT   NOT NULL DEFAULT 'fi_pdmr_manual_export',
    ingested_at       TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (security_id, person_name, transaction_date, transaction_type, volume)
);

CREATE TABLE short_interest (
    security_id    BIGINT NOT NULL REFERENCES security(security_id),
    position_date  DATE   NOT NULL,
    pct_of_shares  DOUBLE NOT NULL,   -- sammanlagd rapporterad nettoblankning, %
    source         TEXT   NOT NULL DEFAULT 'fi_blankning_manual_export',
    ingested_at    TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (security_id, position_date, source)
);
