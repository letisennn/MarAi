-- 0003: discovery-logg + paper trading-skelett (spec-brief §18).
--
-- En "discovery" är en tidsstämplad ögonblicksbild: "vid det här datumet såg
-- bolaget X ut så här (score, fas, features, motivering, analog-statistik)".
-- discovery_outcome fylls i efterhand från price_clean / target_panel när
-- horisonten passerat. Ingen automatisk tracking byggd än — datamodellen finns
-- så att Market Radar / Daily Discoveries / Performance kan bygga på samma spine.

CREATE TABLE discovery (
    discovery_id     BIGINT PRIMARY KEY,
    security_id      BIGINT NOT NULL REFERENCES security(security_id),
    as_of_date       DATE   NOT NULL,          -- observationens datum (point-in-time)
    created_at       TIMESTAMP NOT NULL DEFAULT now(),
    source           TEXT   NOT NULL DEFAULT 'manual',   -- 'manual' | 'daily_picks' | 'radar'
    entry_price_sek  DOUBLE,                   -- justerad close vid as_of_date
    discovery_score  DOUBLE,                   -- preliminär/experimentell score 0..100
    score_version    TEXT,
    phase_key        TEXT,                     -- marknadsfas-nyckel (marc.discovery.phase)
    phase_idx        INTEGER,
    feature_snapshot JSON,                     -- {feature_name: value} känt vid as_of_date
    reason           TEXT,                     -- klartext "varför är detta intressant"
    analogue_stats   JSON,                     -- resultat från analog-motorn vid skapandet
    notes            TEXT,
    UNIQUE (security_id, as_of_date, source)
);

CREATE TABLE discovery_outcome (
    discovery_id     BIGINT NOT NULL REFERENCES discovery(discovery_id),
    horizon          TEXT   NOT NULL,          -- '1d' | '5d' | '20d' | '30d' | '60d' | '90d' | '180d'
    realized_return  DOUBLE,
    realized_max_return DOUBLE,
    realized_max_dd  DOUBLE,
    evaluated_at     TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (discovery_id, horizon)
);
