# Marc AI

Private internal research tool (Jonas & Hugo) — an AI-driven market-psychology
and discovery engine for Nordic small-cap companies.

**Not a product.** Two users, browser-based, private. The research engine lives
in `src/marc/` as a clean importable package; the Streamlit app in `app/` only
renders it.

## Status

**Version 0.1 (market baseline) is implemented** and runs on a synthetic price
source (offline, deterministic — not market data). End-to-end: universe → price /
volume / market cap → causal features → forward-return targets → DuckDB →
statistical baseline (experiment E1) → pre-registered signal rules → Streamlit
app. See `docs/roadmap.md`, `docs/results/E1.md`, `CLAUDE.md`.

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
