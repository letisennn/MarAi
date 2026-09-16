"""Uppbyggnadspoäng — letar bolag INNAN de syns, motsatsen till momentum-jakt.

PRELIMINÄR, OVALIDERAD (samma status som ``score/composite.py`` — CLAUDE.md
regel 1–2). Discovery Score svarar på "hur starkt rör sig det här bolaget
just nu" — och belönar därför bolag nära årshögsta med stor uppgång bakom
sig. Den frågan har inget informationsövertag: vem som helst som öppnar en
kursgraf ser samma sak (Jonas, 2026-09-16).

Den här scoren svarar på en annan fråga: ser läget ut som INNAN en rörelse,
inte efter. Den belönar tyst kurs + stigande volym/uppmärksamhet i en zon
under (inte vid) årshögsta, och en hård spärr capar poängen för bolag som
redan är nära årshögsta med en stor uppgång bakom sig — de hör hemma i
Rörelser & utbrott, inte här.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from marc.config import setup_score_config


@dataclass
class SetupComponent:
    key: str
    label: str
    score: float          # 0–100
    weight: float
    detail: str


@dataclass
class SetupBreakdown:
    total: float
    band: str
    components: list[SetupComponent] = field(default_factory=list)
    score_version: str = "setup_prelim_v0.1"
    already_visible: bool = False
    note: str = "preliminär — ovaliderad, motsatt inriktning mot Discovery Score"


def _pct_rank(value: float | None, peers: pd.Series) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    s = pd.to_numeric(peers, errors="coerce").dropna()
    if len(s) < 4:
        return None
    return float((s < value).mean() * 100.0)


def _inv_pct_rank(value: float | None, peers: pd.Series) -> float | None:
    """Hög rank = LÅGT värde. Används för 'kursen har inte redan dragit'."""
    p = _pct_rank(value, peers)
    return None if p is None else 100.0 - p


def _mean(vals: list[float | None]) -> float | None:
    xs = [v for v in vals if v is not None]
    return float(np.mean(xs)) if xs else None


def _coiled_zone_score(dist: float | None, cfg: dict) -> float | None:
    """Triangulär poäng på avstånd till 52v-högsta: 0 vid toppen (redan synligt),
    topp vid ``peak_distance`` under toppen, tillbaka till 0 bortom
    ``zero_beyond_distance`` (troligen strukturellt trasigt, inte 'coiled')."""
    if dist is None or (isinstance(dist, float) and np.isnan(dist)):
        return None
    d = abs(min(dist, 0.0))
    peak = cfg["coiled_zone"]["peak_distance"]
    zero_beyond = cfg["coiled_zone"]["zero_beyond_distance"]
    if d <= peak:
        return max(0.0, d / peak) * 100.0 if peak else 0.0
    if d <= zero_beyond:
        span = zero_beyond - peak
        return max(0.0, (zero_beyond - d) / span) * 100.0 if span else 0.0
    return 0.0


def _band(total: float, cfg: dict) -> str:
    label = cfg["bands"][0][1]
    for lim, name in cfg["bands"]:
        if total >= lim:
            label = name
    return label


def assess_setup(feats: dict, peers: pd.DataFrame) -> SetupBreakdown:
    cfg = setup_score_config()
    w = cfg["weights"]

    def col(name: str) -> pd.Series:
        return peers[name] if name in peers.columns else pd.Series(dtype=float)

    rvol = feats.get("rvol_5_60")
    vacc = feats.get("vol_accel")
    sacc = feats.get("search_accel")
    facc = feats.get("forum_accel")
    r1m = feats.get("ret_1m")
    r3m = feats.get("ret_3m")
    dist = feats.get("dist_52w_high")

    volym = _mean([_pct_rank(rvol, col("rvol_5_60")), _pct_rank(vacc, col("vol_accel"))])
    attn = _mean([_pct_rank(sacc, col("search_accel")), _pct_rank(facc, col("forum_accel"))])

    abs_r1 = abs(r1m) if r1m is not None else None
    abs_r3 = abs(r3m) if r3m is not None else None
    lugn = _mean([
        _inv_pct_rank(abs_r1, col("ret_1m").abs()) if abs_r1 is not None else None,
        _inv_pct_rank(abs_r3, col("ret_3m").abs()) if abs_r3 is not None else None,
    ])
    coiled = _coiled_zone_score(dist, cfg)

    comps = [
        SetupComponent(
            "volym_uppbyggnad", "Volym börjar röra sig",
            volym if volym is not None else 50.0, w["volym_uppbyggnad"],
            _volume_phrase(rvol, vacc),
        ),
        SetupComponent(
            "uppmarksamhet", "Uppmärksamhet ökar",
            attn if attn is not None else 50.0, w["uppmarksamhet"],
            _attn_phrase(sacc, facc),
        ),
        SetupComponent(
            "lugn_kurs", "Kursen har inte redan dragit",
            lugn if lugn is not None else 50.0, w["lugn_kurs"],
            _calm_phrase(r1m, r3m),
        ),
        SetupComponent(
            "coiled_zon", "Läge under (inte vid) årshögsta",
            coiled if coiled is not None else 50.0, w["coiled_zon"],
            _zone_phrase(dist),
        ),
    ]
    total = sum(c.score * c.weight for c in comps) / sum(c.weight for c in comps)

    gate = cfg["already_visible_gate"]
    already_visible = bool(
        dist is not None and r3m is not None
        and dist >= gate["dist_52w_high_min"] and r3m >= gate["ret_3m_min"]
    )
    if already_visible:
        total = min(total, float(gate["capped_score"]))

    return SetupBreakdown(
        total=round(total, 1), band=_band(total, cfg), components=comps,
        score_version=cfg.get("score_version", "setup_prelim_v0.1"),
        already_visible=already_visible,
    )


def _volume_phrase(rvol: float | None, vacc: float | None) -> str:
    if rvol is None:
        return "okänd handel"
    txt = f"handel {abs(rvol - 1) * 100:.0f} % {'över' if rvol > 1 else 'under'} normalt"
    if vacc is not None:
        txt += ", stigande" if vacc > 0 else ", fallande" if vacc < 0 else ", oförändrad"
    return txt


def _attn_phrase(sacc: float | None, facc: float | None) -> str:
    bits = []
    if sacc is not None:
        bits.append(f"sök {sacc * 100:+.0f} %")
    if facc is not None:
        bits.append(f"forum {facc * 100:+.0f} %")
    return ", ".join(bits) if bits else "ingen attention-data"


def _calm_phrase(r1m: float | None, r3m: float | None) -> str:
    if r1m is None:
        return "okänd kursrörelse"
    txt = f"kurs {r1m * 100:+.0f} % (1 mån)"
    if r3m is not None:
        txt += f", {r3m * 100:+.0f} % (3 mån)"
    return txt


def _zone_phrase(dist: float | None) -> str:
    if dist is None:
        return "okänt läge mot årshögsta"
    if dist >= -0.06:
        return "vid årshögsta — redan synligt för alla, inget övertag här"
    return f"{abs(dist) * 100:.0f} % under årshögsta"
