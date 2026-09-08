# Methodology — bias avoidance and statistical protocol

Status: **proposed**, pending review. Binding once approved.

## 1. Look-ahead bias / data leakage

1. **ISIN as primary key.** Ticker/MIC changes live in `security_xref` with
   validity ranges. Never join on ticker.
2. **Knowable-time filter.** Every raw row has `event_time` (UTC). Feature
   queries use `event_time <= t`. Anything released at/after the exchange close
   counts as next session's information.
3. **Unadjusted prices.** Adjustment factors are derived from `corporate_action`
   and applied as-of `t`. A split after `t` never rewrites pre-`t` returns.
4. **Bitemporal storage** for revised series (shares outstanding now;
   fundamentals/estimates later): economic date + knowledge time.
5. **Causal feature functions.** Pure series→series. Enforced by `hypothesis`
   property tests: `feature(shift(x, k)) == shift(feature(x), k)` and no window
   references future bars.
6. **Cross-sectional stats use only that date's cross-section** — no full-sample
   z-scores or winsorisation bounds.
7. **Layer separation.** `marc.features` must not import `marc.targets`
   (CI check). Targets use future data by design and live only in `target_panel`.
8. **Purged + embargoed splits.** Chronological only. Purge overlapping-window
   observations around any train/test boundary; embargo = longest target horizon
   (180 trading days). (López de Prado.)
9. **Data vintages.** Ingestion stamps `vintage_id`; experiments record which
   vintages + `code_git_sha` they used. Late-arriving history cannot silently
   change past results.

## 2. Survivorship bias

1. **Time-varying universe.** "The universe on date `t`" is an as-of query
   against `universe_membership`, never `SELECT * FROM security`.
2. **Dead names stay in the panel.** The seed universe deliberately includes
   ~30–50 delisted / acquired / bankrupt Nordic names so the code path is
   exercised from day one.
3. **Delisting-return convention** (confirmed 2026-09-08):
   - Bankruptcy / liquidation → terminal return −100% at the delisting date;
     path ends there (an event flag cannot trigger upward afterwards).
   - Acquisition / merger → final price = the offer / cash price (**not** the
     last traded price); if that is ≥ +50% vs P0 within the window, the event
     counts (it was a real +50%).
   - Suspension → carry last price, flag as stale; no new gated highs/lows while
     suspended.
   - No forward-fill past the delisting date.
4. **Size exits** keep the name queryable, flagged `in_universe = false`.
5. **Free-data caveat.** yfinance/Stooq drop delisted tickers → v0.1 universe is
   knowingly incomplete; documented as a gating limitation.

## 3. Statistical protocol

- **Observation unit:** weekly, Friday close (reduces overlapping-window
  autocorrelation vs daily). Daily can be added later.
- **Cap segment:** each observation is tagged `cap_segment_at_entry` ∈
  {small, mid} from its point-in-time market cap (`small` ≤ SEK 1.7bn ≈
  EUR 150m). Headline analysis filters to `small`; `mid` observations (former
  small-caps that grew past the ceiling) are retained only for a separate
  "growing out of small-cap" study.
- **Base price P0:** forward returns and event thresholds use
  P0 = trailing 5-trading-day mean of the adjusted close (sessions `[t-4, t]`),
  not a single `close(t)`, so one anomalously low print cannot make a threshold
  artificially easy. 10-day mean reported as robustness. (`config/targets.yml`)
- **Turnover gate:** a day counts toward an event / max-return / drawdown /
  time-to-peak only if its SEK turnover ≥ `max(SEK 250k, 0.5 × trailing 60-day
  median daily turnover)`. Single thin trades that print an extreme high or low
  are ignored.
- **Control / base rate:** unconditional event rates over the same observation
  set, sliced by year / country / cap segment and pooled. Every conditional
  result is reported as `P(event|cond)`, `P(event|¬cond)`, difference with CI,
  and lift = `P(event|cond) / P(event|pooled)`.
- **Univariate:** weekly cross-sectional quintile sorts per feature; pooled
  forward return + event rate per quintile; Q5−Q1 spread; weekly Spearman IC →
  mean IC + Newey-West t-stat; block bootstrap over weeks (block ≈ 26 weeks) for
  CIs.
- **Multivariate:** Fama-MacBeth — weekly OLS of forward return on standardised
  features across names; average coefficients; Newey-West t-stats.
- **Multiple testing:** pre-register the feature × horizon × metric grid; report
  the family size; Benjamini-Hochberg FDR at q = 0.10.
- **Out-of-sample:** discovery on 2020–2024; a single locked evaluation on
  2025-01 → 2026-06. The holdout is not touched during exploration.
- **Hypothesis generation ≠ testing.** Exploratory findings are promoted into
  `src/marc/` and re-tested on the holdout before being believed.
- **Record everything**, including nulls and broken rules, in
  `experiment_result`; write up in `docs/results/`.

## 4. Backtest framing

Backtests measure **information content**, not tradeable PnL. They ignore market
impact, borrow cost, and execution timing. Any portfolio-style output is
equal-weight, weekly-rebalanced, with liquidity caveats stated.
