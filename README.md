# Noel AI

Private internal research tool (Jonas & Hugo) — a market-discovery /
market-psychology engine for Nordic small-cap companies. Measures changes in
attention, volume and momentum, places companies in a hype-cycle phase, and
compares the current situation to historical analogues.

**Not a product.** Two users, browser-based, private. The research engine lives
in `src/marc/` as a clean importable package (internal name kept); the Streamlit
app in `app/` only renders it.

## Status

**Version 0.1 (market baseline) is implemented**, running on **real Yahoo Finance
data** (~80 Nordic tickers; `--source synthetic` for offline/demo). End-to-end:
universe → price / volume / market cap → causal features → forward-return targets
→ DuckDB → statistical baseline (experiment E1) → pre-registered signal rules →
Streamlit app.

On top of that: **Market Radar** (discovery ranking + hype-cycle phase),
**Historical Analogues** (point-in-time kNN over the feature panel → forward
outcome distribution vs a control group), **Signal Lab** (interactive signal ×
target × universe tests with bootstrap CIs), **Daily Discoveries**, and a
**paper-trading** datamodel (`marc discovery snapshot` / `evaluate`). All of it
is labelled experimental / unvalidated. See `docs/roadmap.md`,
`docs/results/E1.md`, `CLAUDE.md`.

## Documents

| File | What |
|---|---|
| `CLAUDE.md` | Project philosophy + hard rules. Read first. |
| `docs/marc_ai_spec.md` | Full specification (sections 1–39). |
| `docs/archive/` | Out-of-scope / superseded material. Not part of the direction. |
| `docs/architecture.md` | Tech stack, data flow, module responsibilities. |
| `docs/data_sources.md` | Free vs paid sources, historical depth, licensing, MVP-critical vs later. |
| `docs/methodology.md` | Look-ahead / survivorship / leakage avoidance; statistical protocol. |
| `docs/roadmap.md` | Version 0.1 → 1.0 scope. |
| `docs/decisions/` | Architecture decision records (ADRs). |
| `docs/experiments/E1.md` | Pre-registration of the first statistical experiment. |
| `config/universe.yml` | Universe definition (cap band, cap-segment tag, venues, liquidity floor). |
| `config/targets.yml` | Locked target-construction parameters (base price P0, turnover gate, horizons). |

## Quick start

```
uv sync --extra dev
uv run marc pipeline --source synthetic --reset   # build data/marc.duckdb
uv run streamlit run app/Home.py                   # open the app
```

`uv run marc info` shows table row counts. `uv run pytest` runs the suite
(includes one integration test that rebuilds the pipeline in a temp DB).
Switch to real (survivorship-biased, rate-limited) prices with
`--source yfinance`.
