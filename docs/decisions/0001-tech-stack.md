# ADR 0001 — Tech stack

- Status: **proposed** (awaiting Jonas/Hugo sign-off)
- Date: 2026-09-08

## Context

Private research tool for two users. Optimise for fast internal iteration, not
public scalability. Spec requires point-in-time correctness, corporate-action
handling, reproducibility, and a statistics-first workflow (stats → ML → LLM).

## Decision

| Area | Choice | Why |
|---|---|---|
| Engine language | Python 3.11+, `src/` layout, `uv` | Whole spec is stats/ML/LLM. |
| Database | **DuckDB** single file; raw dumps as immutable Parquet/JSON registered as views | ACID SQL, zero ops, columnar, great Arrow/pandas/Polars interop. Satisfies spec §33. Chosen over Postgres+Parquet for simplicity (2 users, batch workload) and over SQLite for analytics power. Portable schema keeps a Postgres move mechanical. |
| Migrations | Numbered `.sql` + small runner + `schema_migrations` | No Alembic for DuckDB; keep portable. |
| Transforms | Polars (lazy) for panels; pandas at the stats boundary | Speed + Arrow; pandas where statsmodels/sklearn need it. |
| Stats | numpy, scipy, statsmodels (Fama-MacBeth, Newey-West, BH-FDR) | Baseline before ML. |
| CLI / scheduling | Typer (`marc <verb>`) + Makefile + cron | No heavy orchestrator for 2 users. Prefect only if v0.3+ pipelines get complex. |
| Web app | **Streamlit**, read-only against DuckDB; all logic in `marc` | Fastest iteration. Swappable for FastAPI+React later without touching the engine. |
| Quality | ruff, mypy (strict), pytest + hypothesis, pre-commit | Causality property tests are load-bearing here. |
| ML | scikit-learn → LightGBM/XGBoost | Deferred to v0.7. |
| LLM | Anthropic SDK | Deferred to v0.5. Handles unstructured text only; no quantitative claims. |

## Consequences

- Single-writer DB: the pipeline holds the write connection; Streamlit opens
  read-only. Fine for batch research with two users; revisit if we need
  concurrent writers or a hosted multi-user app.
- No BFF/API layer in v0.1. `marc` *is* the backend if we need one later.
- Free price data (yfinance/Stooq) is survivorship-biased; v0.1 universe is
  knowingly incomplete until a paid source is signed off.

## Alternatives considered

- **Postgres (Docker) + Parquet/DuckDB analytical layer** — more robust for
  live ingestion and concurrency; rejected as over-engineered for now, kept as
  the documented scale path.
- **DuckDB-only** — chosen.
- **FastAPI + React** web app — rejected for v0.1 (two languages, slow
  iteration); revisit near v1.0.
- **Jupyter/Marimo only** — rejected; we want a persistent browsable app early.
