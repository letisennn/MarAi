"""Target construction — forward returns and large-move events.

Uses FUTURE data by design. Targets are only ever joined to features for
training/evaluation; they are never fed back as a feature. This package must not
be imported by marc.features.

Parameters are locked in config/targets.yml (target_set_version). Key rules:
  - Base price P0 = trailing 5-trading-day mean of the ADJUSTED close [t-4, t],
    used as the denominator for every forward metric.
  - Turnover gate: a day contributes to an event / max-return / drawdown /
    time-to-peak only if its SEK turnover >= max(250k, 0.5 * 60d median).
  - Delisting inside a window: bankruptcy -> terminal -100%; acquisition ->
    terminal offer/cash price; suspension -> carry last price (docs/methodology.md 2.3).

forward_returns.py builds target_panel:
  fwd_ret_{5,20,30,60,90,180}, fwd_ret_h_sm (robustness)
  up_10_5d, up_25_20d, up_50_30d, up_50_60d, up_50_90d, up_100_180d
  fwd_max_ret_h, fwd_max_dd_h, days_to_peak_h, sustained_h

Not implemented.
"""
