# Architecture

Status: **v0.1 implemented** (on the synthetic price source). The shape below is
what runs today; `marc/backtest`, `marc/ml`, `marc/llm` and `marc/reporting`
remain scaffold.

## 1. Shape of the system

Two processes, one file:

```
  ┌─────────────────────────────┐         ┌──────────────────────┐
  │  pipeline (read-write)      │         │  Streamlit (read-only)│
  │  marc.* package + Typer CLI │──────►  │  app/ — imports marc  │
  └─────────────┬───────────────┘         └───────────┬──────────┘
                │                                     │
                ▼                                     ▼
        data/marc.duckdb  ◄───── registered views ──── data/raw/*.parquet
        (curated tables)                               (immutable source dumps)
```

- **DuckDB is the database** (ACID, SQL, single file). It satisfies spec §33 —
  we are not relying on disconnected CSVs.
- **Raw source dumps** are written once as Parquet/JSON under `data/raw/`,
  keyed by `vintage_id`, and never mutated. They are provenance and let us
  rebuild curated tables from scratch.
- No network API between pipeline and app in v0.1. If we later want a real
  backend, `marc` already is that backend — wrap it in FastAPI, leave the
  engine untouched.

## 2. Module responsibilities (spec §32)

| Module | Responsibility | Writes |
|---|---|---|
| `marc/ingestion` | Per-source adapters behind a common `Source` protocol. Parse only, no transformation. Idempotent. | `price_daily`, `shares_outstanding`, `fx_rate_daily`, `ingestion_run`, `data_vintage` |
| `marc/reference` | `security` + ISIN xref history, corporate actions, listing-status history, time-varying `universe_membership` (as-of logic). OpenFIGI/ISIN mapping. | `security`, `security_xref`, `corporate_action`, `listing_status_history`, `universe_membership` |
| `marc/cleaning` | Validation (price sanity, non-negative volume, cross-source dedup, outlier flags), FX conversion to base ccy, as-of adjustment factors, delisting-return stitching. Nothing dropped silently. | `adjustment_factor`, `market_cap_daily`, cleaned views |
| `marc/features` | Pure **causal** functions series→series, assembled per observation date. Versioned feature sets. Must not import `marc.targets`. | `observation`, `feature_panel` |
| `marc/targets` | Forward returns / events per horizon. Uses future data **by design**; only ever joined to features for train/eval, never fed back. | `target_panel` |
| `marc/signals` | Rule-based flags from features (v0.1). No fitted weights. | `signal_log` |
| `marc/score` | **Preliminary** composite score (`config/score.yml`, hand-set weights). Pure function; app renders it labelled "ovaliderad". To be replaced by a stats/ML-derived, OOS-validated weight. | — |
| `marc/stats` | Baseline rates, univariate sorts, IC, control comparisons, Fama-MacBeth, block bootstrap, BH-FDR. | `experiment`, `experiment_result` |
| `marc/backtest` | Event studies + simple portfolio formation, purged/embargoed splits. Reports information content, not PnL. | `experiment_result`, `signal_outcome` |
| `marc/ml` | v0.7 — scaffold only. | — |
| `marc/llm` | v0.5 — scaffold only. | — |
| `marc/reporting` | Figures/tables for the app and write-ups. | — |
| `app/` | Streamlit pages. No business logic. | — |

## 3. Identifiers & time

- **Primary key is ISIN** (mapped to an internal `security_id`). Tickers and MICs
  change; they live in `security_xref` with `valid_from`/`valid_to`. Never join
  on ticker outside that table.
- Every raw row carries `event_time` (when it was knowable, UTC) and
  `ingested_at`. Feature queries filter `event_time <= t`.
- Anything revised (shares outstanding, later fundamentals/estimates) is
  **bitemporal**: economic date + knowledge time.
- Prices are stored **unadjusted**. `adjustment_factor` is derived from
  `corporate_action` and applied as-of `t`, so a split after `t` never rewrites
  pre-`t` returns.

## 4. Reproducibility

- Each ingestion run stamps a `vintage_id` in `data_vintage`.
- Each `experiment` records `code_git_sha` and the `data_vintage_ids` it used.
- A signal in `signal_log` stores its full `feature_snapshot`, so it can be
  reconstructed exactly.

## 5. Tech choices — see `docs/decisions/0001-tech-stack.md`

Python 3.11 + uv · DuckDB · Polars (transforms) / pandas (stats boundary) ·
statsmodels/scipy · Typer CLI + Makefile + cron · Streamlit · ruff/mypy/pytest +
hypothesis.
