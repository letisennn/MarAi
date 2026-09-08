"""Preliminär composite-score — handsatta vikter, OVALIDERAD (CLAUDE.md regel 1–2).

Rena funktioner, ingen databas. ``assess`` tar en akties senaste mätvärden, en
peer-ram (ett rad per bolag i universumet samma vecka) och antalet mönster som
lyst, och returnerar en 0–100-poäng med en uppdelning i klartext.

Poängen är ett arbetsverktyg. Den bevisar ingenting och får bara visas märkt
"preliminär — ovaliderade vikter" bredvid basnivån.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from marc.config import score_config


@dataclass
class Component:
    key: str
    label: str
    score: float          # 0–100
    weight: float
    detail: str           # klartext


@dataclass
class ScoreBreakdown:
    total: float                       # 0–100
    band: str                          # "Svag" ... "Mycket stark"
    components: list[Component] = field(default_factory=list)
    score_version: str = "prelim_v0.1"
    note: str = "preliminär — ovaliderade vikter"


def _pct_rank(value: float | None, peers: pd.Series) -> float | None:
    """Percentil (0–100) för ``value`` bland ``peers``. None om otillräckligt underlag."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    s = pd.to_numeric(peers, errors="coerce").dropna()
    if len(s) < 4:
        return None
    return float((s < value).mean() * 100.0)


def _rank_word(pct: float | None) -> str:
    if pct is None:
        return "otillräckligt underlag för jämförelse"
    if pct >= 80:
        return "starkare än ~8 av 10 bolag i universumet just nu"
    if pct >= 60:
        return "starkare än de flesta bolag just nu"
    if pct >= 40:
        return "mitt i fältet"
    if pct >= 20:
        return "svagare än de flesta bolag just nu"
    return "bland de svagaste i universumet just nu"


def _mean(vals: list[float | None]) -> float | None:
    xs = [v for v in vals if v is not None]
    return float(np.mean(xs)) if xs else None


def _band(total: float) -> str:
    label = "Svag"
    for lim, name in score_config()["bands"]:
        if total >= lim:
            label = name
    return label


def assess(feats: dict, peers: pd.DataFrame, n_rules: int) -> ScoreBreakdown:
    cfg = score_config()
    w = cfg["weights"]

    def col(name: str) -> pd.Series:
        return peers[name] if name in peers.columns else pd.Series(dtype=float)

    p_r3 = _pct_rank(feats.get("ret_3m"), col("ret_3m"))
    p_r6 = _pct_rank(feats.get("ret_6m"), col("ret_6m"))
    p_r12 = _pct_rank(feats.get("ret_12m"), col("ret_12m"))
    p_dist = _pct_rank(feats.get("dist_52w_high"), col("dist_52w_high"))
    p_rvol = _pct_rank(feats.get("rvol_5_60"), col("rvol_5_60"))
    p_vacc = _pct_rank(feats.get("vol_accel"), col("vol_accel"))

    momentum = _mean([p_r3, p_r6, p_r12])
    narhet = p_dist
    volym = _mean([p_rvol, p_vacc])
    monster = min(max(n_rules, 0), 3) / 3.0 * 100.0

    r3 = feats.get("ret_3m")
    dist = feats.get("dist_52w_high")
    rvol = feats.get("rvol_5_60")

    comps = [
        Component(
            "momentum", "Momentum", momentum if momentum is not None else 50.0, w["momentum"],
            (f"kurs {r3:+.0%} senaste 3 mån — {_rank_word(momentum)}" if r3 is not None
             else "för kort historik"),
        ),
        Component(
            "narhet_arshogsta", "Nära årshögsta", narhet if narhet is not None else 50.0,
            w["narhet_arshogsta"],
            (f"{abs(dist):.0%} under årshögsta — {_rank_word(narhet)}" if dist is not None
             else "okänt läge"),
        ),
        Component(
            "volymintresse", "Handel & intresse", volym if volym is not None else 50.0,
            w["volymintresse"],
            (_volume_phrase(rvol) + f" — {_rank_word(volym)}" if rvol is not None
             else "okänd handel"),
        ),
        Component(
            "monster", "Mönster", monster, w["monster"],
            (f"{n_rules} av 3 förregistrerade mönster har lyst de senaste veckorna"
             if n_rules else "inget mönster har lyst de senaste veckorna"),
        ),
    ]

    total = sum(c.score * c.weight for c in comps) / sum(c.weight for c in comps)
    return ScoreBreakdown(total=round(total, 1), band=_band(total), components=comps,
                          score_version=cfg.get("score_version", "prelim_v0.1"))


def _volume_phrase(rvol: float) -> str:
    d = rvol - 1.0
    if abs(d) < 0.10:
        return "handel på normal nivå"
    return f"{abs(d) * 100:.0f} % {'högre' if d > 0 else 'lägre'} handel än normalt"
