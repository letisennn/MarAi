-- 0001_init.sql — PROPOSED schema for review. NOT APPLIED.
-- DuckDB dialect, kept portable so a later move to Postgres is mechanical.
-- Surrogate keys via sequences; JSON stored as JSON/TEXT; timestamps in UTC.

-- ---------------------------------------------------------------------------
-- migration bookkeeping
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    applied_at  TIMESTAMP NOT NULL DEFAULT now(),
    checksum    TEXT
);

-- ===========================================================================
-- REFERENCE
-- ===========================================================================
CREATE SEQUENCE seq_security_id START 1;

CREATE TABLE security (
    security_id       BIGINT PRIMARY KEY DEFAULT nextval('seq_security_id'),
    isin              TEXT NOT NULL UNIQUE,
    figi              TEXT,
    name              TEXT NOT NULL,
    country           TEXT NOT NULL CHECK (country IN ('SE','NO','DK','FI')),
    base_listing_mic  TEXT,
    currency          TEXT NOT NULL,
    sector            TEXT,
    industry          TEXT,
    share_class       TEXT,
    first_listed_date DATE,
    status            TEXT NOT NULL DEFAULT 'listed'
                       CHECK (status IN ('listed','delisted','acquired','bankrupt','suspended')),
    status_date       DATE,     -- denormalised convenience: delisting/acquisition/bankruptcy date
    status_detail     TEXT,     -- e.g. acquisition offer price (local ccy) or a note; canonical detail lives in listing_status_history / corporate_action
    created_at        TIMESTAMP NOT NULL DEFAULT now()
);

-- ticker / MIC / name changes over time. Never join on ticker outside this table.
CREATE TABLE security_xref (
    security_id  BIGINT NOT NULL REFERENCES security(security_id),
    id_type      TEXT NOT NULL CHECK (id_type IN ('ticker','mic','isin','figi','name')),
    id_value     TEXT NOT NULL,
    valid_from   DATE NOT NULL,
    valid_to     DATE,                      -- NULL = still current
    source       TEXT NOT NULL,
    PRIMARY KEY (security_id, id_type, id_value, valid_from)
);

CREATE TABLE listing_status_history (
    security_id     BIGINT NOT NULL REFERENCES security(security_id),
    status          TEXT NOT NULL
                     CHECK (status IN ('listed','delisted','acquired','bankrupt','suspended')),
    market_segment  TEXT,                    -- main / first_north / spotlight / ngm / euronext_growth ...
    valid_from      DATE NOT NULL,
    valid_to        DATE,
    delisting_return DOUBLE,                 -- terminal return applied at valid_from when leaving 'listed'
    reason          TEXT,
    source          TEXT NOT NULL,
    PRIMARY KEY (security_id, valid_from)
);

CREATE SEQUENCE seq_ca_id START 1;
CREATE TABLE corporate_action (
    ca_id        BIGINT PRIMARY KEY DEFAULT nextval('seq_ca_id'),
    security_id  BIGINT NOT NULL REFERENCES security(security_id),
    action_type  TEXT NOT NULL CHECK (action_type IN
                  ('split','dividend','rights','spinoff','ticker_change',
                   'merger','acquisition','delisting','bankruptcy')),
    announce_date DATE,
    ex_date       DATE,
    record_date   DATE,
    pay_date      DATE,
    ratio         DOUBLE,                    -- e.g. split 3:1 -> 3.0
    cash_amount   DOUBLE,
    currency      TEXT,
    details       JSON,
    source        TEXT NOT NULL,
    ingested_at   TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE universe_membership (
    universe_name     TEXT NOT NULL,
    security_id       BIGINT NOT NULL REFERENCES security(security_id),
    valid_from        DATE NOT NULL,
    valid_to          DATE,
    entry_reason      TEXT,
    exit_reason       TEXT,
    criteria_snapshot JSON,                  -- thresholds + measured values at entry
    PRIMARY KEY (universe_name, security_id, valid_from)
);

CREATE TABLE exchange_session (
    mic          TEXT NOT NULL,
    session_date DATE NOT NULL,
    is_trading   BOOLEAN NOT NULL,
    PRIMARY KEY (mic, session_date)
);

-- ===========================================================================
-- RAW MARKET DATA (immutable; one row per source observation)
-- ===========================================================================
CREATE TABLE data_vintage (
    vintage_id     TEXT PRIMARY KEY,         -- e.g. 'yfinance:2026-09-08T12:00Z'
    source         TEXT NOT NULL,
    pulled_at      TIMESTAMP NOT NULL,
    coverage_start DATE,
    coverage_end   DATE,
    n_rows         BIGINT,
    params         JSON,
    notes          TEXT
);

CREATE SEQUENCE seq_run_id START 1;
CREATE TABLE ingestion_run (
    run_id      BIGINT PRIMARY KEY DEFAULT nextval('seq_run_id'),
    source      TEXT NOT NULL,
    started_at  TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status      TEXT NOT NULL CHECK (status IN ('running','ok','failed')),
    n_in        BIGINT,
    n_rejected  BIGINT,
    log_ref     TEXT
);

CREATE TABLE price_daily (
    security_id  BIGINT NOT NULL REFERENCES security(security_id),
    session_date DATE NOT NULL,
    mic          TEXT,
    open         DOUBLE,
    high         DOUBLE,
    low          DOUBLE,
    close        DOUBLE,                     -- UNADJUSTED
    volume       DOUBLE,
    turnover     DOUBLE,
    currency     TEXT NOT NULL,
    is_adjusted  BOOLEAN NOT NULL DEFAULT FALSE,
    source       TEXT NOT NULL,
    vintage_id   TEXT REFERENCES data_vintage(vintage_id),
    event_time   TIMESTAMP,                  -- session close in UTC (knowable time)
    ingested_at  TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (security_id, session_date, source)
);

-- bitemporal: as_of_date = economic date; knowledge_time = when it was knowable
CREATE TABLE shares_outstanding (
    security_id    BIGINT NOT NULL REFERENCES security(security_id),
    as_of_date     DATE NOT NULL,
    knowledge_time TIMESTAMP NOT NULL,
    shares         DOUBLE NOT NULL,
    source         TEXT NOT NULL,
    vintage_id     TEXT REFERENCES data_vintage(vintage_id),
    PRIMARY KEY (security_id, as_of_date, knowledge_time)
);

CREATE TABLE fx_rate_daily (
    base_ccy     TEXT NOT NULL,
    quote_ccy    TEXT NOT NULL,
    session_date DATE NOT NULL,
    rate         DOUBLE NOT NULL,            -- 1 quote_ccy = rate base_ccy
    source       TEXT NOT NULL,
    PRIMARY KEY (base_ccy, quote_ccy, session_date, source)
);

-- derived from corporate_action; fully recomputable
CREATE TABLE adjustment_factor (
    security_id     BIGINT NOT NULL REFERENCES security(security_id),
    session_date    DATE NOT NULL,
    cum_split_factor DOUBLE NOT NULL DEFAULT 1.0,
    cum_div_factor   DOUBLE NOT NULL DEFAULT 1.0,
    computed_at      TIMESTAMP NOT NULL DEFAULT now(),
    method           TEXT,
    PRIMARY KEY (security_id, session_date)
);

-- ===========================================================================
-- DERIVED / ANALYTICAL
-- ===========================================================================
CREATE TABLE market_cap_daily (
    security_id    BIGINT NOT NULL REFERENCES security(security_id),
    session_date   DATE NOT NULL,
    market_cap_sek DOUBLE,
    shares_used    DOUBLE,
    price_used     DOUBLE,
    fx_used        DOUBLE,
    PRIMARY KEY (security_id, session_date)
);

CREATE SEQUENCE seq_obs_id START 1;
CREATE TABLE observation (
    obs_id               BIGINT PRIMARY KEY DEFAULT nextval('seq_obs_id'),
    security_id          BIGINT NOT NULL REFERENCES security(security_id),
    obs_date             DATE NOT NULL,
    universe_name        TEXT NOT NULL,
    in_universe          BOOLEAN NOT NULL,
    has_min_history      BOOLEAN NOT NULL,
    -- cap segment implied by point-in-time market cap on obs_date:
    -- 'small' if market_cap_sek <= 1.7e9 (~EUR 150m), else 'mid' (former
    -- small-cap that grew; excluded from the main analysis).
    cap_segment_at_entry TEXT CHECK (cap_segment_at_entry IN ('small','mid')),
    market_cap_sek       DOUBLE,          -- point-in-time on obs_date (denormalised from market_cap_daily for slicing)
    feature_set_version  TEXT NOT NULL,
    UNIQUE (security_id, obs_date, universe_name, feature_set_version)
);

CREATE TABLE feature_panel (
    obs_id       BIGINT NOT NULL REFERENCES observation(obs_id),
    feature_name TEXT NOT NULL,
    value        DOUBLE,
    PRIMARY KEY (obs_id, feature_name)
);

-- Targets are built per config/targets.yml (target_set_version). Base price P0 =
-- trailing 5-day mean of the adjusted close; events / max-return / drawdown /
-- time-to-peak only count days that clear the SEK turnover gate. See
-- docs/experiments/E1.md and docs/methodology.md 3.
CREATE TABLE target_panel (
    obs_id             BIGINT NOT NULL REFERENCES observation(obs_id),
    target_set_version TEXT NOT NULL,
    target_name        TEXT NOT NULL,        -- fwd_ret_20, up_50_90d, fwd_max_ret_90, fwd_max_dd_90, days_to_peak_90, sustained_90 ...
    value              DOUBLE,
    PRIMARY KEY (obs_id, target_set_version, target_name)
);

-- ===========================================================================
-- RESEARCH BOOKKEEPING
-- ===========================================================================
CREATE SEQUENCE seq_experiment_id START 1;
CREATE TABLE experiment (
    experiment_id    BIGINT PRIMARY KEY DEFAULT nextval('seq_experiment_id'),
    name             TEXT NOT NULL,
    hypothesis       TEXT NOT NULL,
    prereg_doc       TEXT,                   -- path to docs/experiments/*.md
    spec             JSON,                   -- universe, dates, features, horizons, splits
    code_git_sha     TEXT,
    data_vintage_ids JSON,
    created_at       TIMESTAMP NOT NULL DEFAULT now(),
    status           TEXT NOT NULL DEFAULT 'draft'
                      CHECK (status IN ('draft','registered','run','archived'))
);

CREATE SEQUENCE seq_result_id START 1;
CREATE TABLE experiment_result (
    result_id        BIGINT PRIMARY KEY DEFAULT nextval('seq_result_id'),
    experiment_id    BIGINT NOT NULL REFERENCES experiment(experiment_id),
    metric_name      TEXT NOT NULL,
    subset           JSON,                   -- {"year":2022,"country":"SE","bucket":"micro"}
    value            DOUBLE,
    ci_low           DOUBLE,
    ci_high          DOUBLE,
    n_obs            BIGINT,
    n_events         BIGINT,
    is_out_of_sample BOOLEAN NOT NULL DEFAULT FALSE,
    passed           BOOLEAN,                -- NULL = not a pass/fail metric
    params           JSON,
    created_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE SEQUENCE seq_signal_id START 1;
CREATE TABLE signal_log (
    signal_id        BIGINT PRIMARY KEY DEFAULT nextval('seq_signal_id'),
    security_id      BIGINT NOT NULL REFERENCES security(security_id),
    as_of_date       DATE NOT NULL,
    rule_version     TEXT NOT NULL,
    feature_snapshot JSON NOT NULL,
    score            DOUBLE,                 -- NULL until weights are fitted + validated
    model_version    TEXT,
    created_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE signal_outcome (
    signal_id           BIGINT NOT NULL REFERENCES signal_log(signal_id),
    horizon             TEXT NOT NULL,       -- '5d','20d','30d','60d','90d','180d'
    realized_return     DOUBLE,
    realized_max_return DOUBLE,
    realized_max_dd     DOUBLE,
    realized_event      BOOLEAN,
    evaluated_at        TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (signal_id, horizon)
);

-- Deferred tables (create in their roadmap version):
--   trend_series                       (v0.2)
--   news_item                          (v0.3)
--   social_post                        (v0.4)  -- incl. per-author history for new-vs-returning; GDPR: hash user ids + retention policy first (see docs/data_sources.md)
--   document, llm_annotation           (v0.5)
--   estimate, insider_trade,
--   short_position, ownership_change   (v0.6)
-- The migration runner records schema_migrations itself; do not INSERT here.
