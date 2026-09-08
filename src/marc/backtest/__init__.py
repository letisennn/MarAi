"""Backtesting — measures information content, not tradeable PnL.

- event_study.py : mean cumulative abnormal return around signal dates
                   (-20..+90 trading days) vs equal-weight universe, with CIs.
- portfolio.py   : weekly equal-weight top-quintile vs universe; purge + embargo
                   = 180 trading days at any train/test boundary.

Outputs go to experiment_result and signal_outcome. Liquidity/impact caveats are
always stated. Not implemented.
"""
