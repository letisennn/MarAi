"""Forward-return / large-move-event target construction.

Uses FUTURE data by design. Parameters are locked in ``config/targets.yml``
(see ``docs/experiments/E1.md``):

* base price ``P0`` = trailing 5-trading-day mean of the adjusted close;
* a day only counts toward an event / max-return / drawdown / time-to-peak if its
  SEK turnover clears ``max(abs_min, rel_frac * trailing 60d median turnover)``;
* delisting inside a window: bankruptcy -> terminal -100%; acquisition ->
  terminal offer price; suspension/plain -> path just ends (NaN beyond).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from marc.config import targets_config


@dataclass
class DelistInfo:
    kind: str  # 'acquisition' | 'bankruptcy' | 'suspension' | 'delisting'
    date: pd.Timestamp
    offer_adj_sek: float | None = None


def _config() -> dict:
    cfg = targets_config()
    horizons = [int(h) for h in cfg["horizons_trading_days"]]
    events = [
        (e["name"], float(e["threshold"]), int(e["horizon_trading_days"]))
        for e in cfg["events"]
    ]
    g = cfg["turnover_gate_sek"]
    return {
        "horizons": horizons,
        "events": events,
        "gate_abs": float(g["absolute_min"]),
        "gate_frac": float(g["relative_min_fraction_of_median_60d"]),
        "p0_window": int(cfg["base_price"]["window_trading_days"]),
        "peak_horizons": [30, 90],
    }


def _extend_for_delisting(
    eff: pd.DataFrame, delist: DelistInfo | None, calendar: pd.DatetimeIndex, hmax: int
) -> pd.DataFrame:
    if delist is None or delist.kind in {"suspension", "delisting"}:
        return eff
    last = eff.index.max()
    future = calendar[calendar > last][:hmax]
    if len(future) == 0:
        return eff
    if delist.kind == "bankruptcy":
        px = 1e-6
    else:  # acquisition
        px = float(delist.offer_adj_sek) if delist.offer_adj_sek else float(eff["adj_close"].iloc[-1])
    ext = pd.DataFrame(
        {"adj_close": px, "adj_high": px, "adj_low": px, "turnover_sek": 1e12},
        index=future,
    )
    return pd.concat([eff, ext])


def compute_target_frame(
    df: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    delist: DelistInfo | None = None,
) -> pd.DataFrame:
    """``df``: one security, indexed by session_date, cols adj_close/adj_high/adj_low/turnover_sek."""
    cfg = _config()
    hmax = max(cfg["horizons"])
    eff = _extend_for_delisting(df[["adj_close", "adj_high", "adj_low", "turnover_sek"]].copy(),
                                delist, calendar, hmax)
    n = len(eff)
    pos = np.arange(n)

    p0 = eff["adj_close"].rolling(cfg["p0_window"], min_periods=cfg["p0_window"]).mean()
    med60 = eff["turnover_sek"].rolling(60, min_periods=20).median()
    gate = np.maximum(cfg["gate_abs"], cfg["gate_frac"] * med60)
    gpass = eff["turnover_sek"] >= gate
    hi_g = eff["adj_high"].where(gpass)
    lo_g = eff["adj_low"].where(gpass)

    out: dict[str, pd.Series] = {}
    fwd_ret: dict[int, pd.Series] = {}
    fwd_max_ret: dict[int, pd.Series] = {}
    fwd_max_hi: dict[int, pd.Series] = {}

    for h in cfg["horizons"]:
        fr = eff["adj_close"].shift(-h) / p0 - 1.0
        mh = hi_g.rolling(h, min_periods=1).max().shift(-h)
        ml = lo_g.rolling(h, min_periods=1).min().shift(-h)
        mr = mh / p0 - 1.0
        dd = ml / p0 - 1.0
        fwd_ret[h] = fr
        fwd_max_ret[h] = mr
        fwd_max_hi[h] = mh
        out[f"fwd_ret_{h}"] = fr
        out[f"fwd_max_ret_{h}"] = mr
        out[f"fwd_max_dd_{h}"] = dd
        sustained = (fr >= 0.5 * mr).astype("float64")
        out[f"sustained_{h}"] = sustained.where(fr.notna() & mr.notna())

    for name, thr, h in cfg["events"]:
        mh = fwd_max_hi[h]
        complete = pd.Series(pos + h < n, index=eff.index)
        reached = mh >= thr * p0
        ev = pd.Series(np.nan, index=eff.index)
        ev = ev.mask(reached, 1.0)
        ev = ev.mask(~reached & complete & p0.notna(), 0.0)
        out[name] = ev

    hi_vals = hi_g.to_numpy()
    for h in cfg["peak_horizons"]:
        dtp = np.full(n, np.nan)
        for i in range(n):
            w = hi_vals[i + 1 : i + 1 + h]
            if w.size and np.any(np.isfinite(w)):
                dtp[i] = int(np.nanargmax(w)) + 1
        out[f"days_to_peak_{h}"] = pd.Series(dtp, index=eff.index)

    return pd.DataFrame(out, index=eff.index).reindex(df.index)
