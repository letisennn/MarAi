# Roadmap

Follows `marc_ai_spec.md` §36.

| Version | Adds | Question it answers |
|---|---|---|
| **0.1** | Universe, price/volume/market cap, causal features, forward-return targets, DuckDB, statistical baseline (E1), simple backtest | Does simple price/volume behaviour carry information about forward returns? |
| 0.2 | Google/search activity, search acceleration, abnormal search | Does attention add information beyond price/volume? |
| 0.3 | News frequency/acceleration, sentiment, catalyst classification, market reaction | Does news flow add information? |
| 0.4 | Mentions, unique/new participants, engagement, discussion acceleration, sentiment | Do changes in participation/opinion add information? |
| 0.5 | LLM: narrative detection, narrative change, emerging themes, spread, hype stage | What are people beginning to believe? |
| 0.6 | Analyst estimates + revisions, insider activity, short interest, ownership, earnings-call analysis | How do market expectations relate to behaviour? |
| 0.7 | Machine learning on the accumulated feature store | Do signal combinations improve out-of-sample performance? |
| 1.0 | Live scanner over the Nordic small-cap universe | Ranked list of potential discoveries (not predictions). |

## Version 0.1 — concrete deliverables

**Status: implemented on the synthetic price source.** `[x]` done, `[~]` partial,
`[ ]` deferred. Results: `docs/results/E1.md`. Run: `uv run marc pipeline
--source synthetic --reset` then `uv run streamlit run app/Home.py`.

- `[x]` 1–7, 9, 10, 12, 13 below.
- `[~]` 8 targets — built; long multibagger horizons intentionally dropped.
- `[~]` 11 backtest B1 — quintile / event-lift analysis lives in `marc.stats`;
  the dedicated event-study + purged-portfolio module is deferred to v0.1.1.
- `[~]` 14 docs — architecture / data_sources / methodology / ADR-0001 written;
  will be revised when a real price source lands.
- `[ ]` BH-FDR multiple-testing control; Newey-West SEs for Fama-MacBeth.

1. Concrete `config/universe.yml` (admission market cap SEK 50m–1.7bn;
   `cap_segment_at_entry` small/mid tag with retention after growth; First North
   + Spotlight + NGM included) + `config/targets.yml`. Reviewed by Jonas 2026-09-08.
2. DuckDB + migration runner + `migrations/0001_init.sql` applied.
3. Seed security list (~150–300 Nordic names, **incl. ~30–50 delisted/acquired/
   bankrupt**); ISIN via OpenFIGI.
4. `yfinance` + `stooq` ingestion adapters: unadjusted daily OHLCV
   2018-01-01→today for the seed list; `ingestion_run` + `data_vintage`.
   Börsdata/EODHD adapters stubbed (interface + docstrings only).
5. Cleaning: validation rules, FX→SEK (Riksbank/ECB), adjustment factors from
   splits/divs, delisting-return stitching for the seeded dead names (manually
   seeded corporate actions).
6. `universe_membership` builder: month-end 2020–2026, point-in-time market-cap
   test → as-of membership.
7. ~15–20 causal features (`v0.1`), property-tested.
8. Targets (`config/targets.yml`): base price P0 = trailing 5-day mean adjusted
   close; forward returns {5,20,30,60,90,180}d; events {+10/5, +25/20, +50/30,
   +50/60, +50/90, +100/180} on gated intraday highs (day counts only if
   turnover ≥ max(SEK 250k, 0.5× 60d median)); fwd max return, fwd max drawdown,
   time-to-peak, sustained flag (all gated).
9. Panel build: weekly observations (Fridays) 2020-01→2026-06 for in-universe
   names → `observation` + `feature_panel` + `target_panel`.
10. Experiment E1 (a–d) per `docs/experiments/E1.md`; all results incl. nulls to
    `experiment_result` + write-up in `docs/results/E1.md`.
11. Backtest B1: event study + weekly top-quintile vs universe, purge/embargo
    180 trading days.
12. Streamlit: 4 read-only pages (Universe as-of, Security detail, E1 results,
    Signal log).
13. Tests: feature causality, target correctness, universe as-of, delisting
    return.
14. Fill in `architecture.md`, `data_sources.md`, `methodology.md`, ADR-0001.

### Tillägg 2026-09-08 (Jonas)

- **Preliminär composite-score** (`src/marc/score/`, `config/score.yml`): handsatt,
  ovaliderad 0–100-poäng per aktie + uppskattat historiskt rörelsespann. Visas i
  appen märkt "preliminär — ovaliderade vikter", bredvid basnivån. Ersätts av en
  statistik-/ML-härledd vikt (E1 / v0.7).
- **Appen omgjord till svenska klarspråk** kring bolaget: `Start`, `Bolag`
  (screener med score), `Bolag i detalj` (bedömning + varför + läget i klartext),
  `Signaler`, `Forskning`.
- **v0.2–0.4 tidigarelagda:** Google Trends, nyhetsrubriker och forum/social
  byggs parallellt med syntetisk källa först (som pris), riktiga adaptrar som
  `--source`. Se `docs/data_sources.md`.

**INTE i v0.1:** LLM, ML, betalda API:er. Score:n och uppsideuppskattningen får
inte visas utan "preliminär/ovaliderad"-märkning förrän de validerats.

**Exit criterion:** we can state, with CIs and an untouched holdout result,
whether simple price/volume features carry statistically meaningful information
about forward returns/events in the (as far as free data allows)
survivorship-handled Nordic small-cap panel. "No / weak" is an acceptable,
documented outcome.
