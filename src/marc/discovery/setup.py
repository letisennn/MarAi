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


def compute_setup_score_panel(wide: pd.DataFrame, exclude_already_visible: bool = False) -> pd.Series:
    """Vektoriserad Uppbyggnadspoäng över hela panelen (en rad per bolag×vecka)
    — exakt samma formel/vikter/spärr som ``assess_setup`` (config/setup_score.yml),
    bara snabb nog att köra på hela historiken istället för en UI-rad i taget.

    Byggd 2026-09-19 (Jonas: "bygg den så den har en edge") för att kunna svepa
    Uppbyggnadspoängen genom E1:s riktiga statistik (veckovis tvärsnitts-rank-IC,
    kvintilspridning, kronologisk discovery/holdout-split) — samma rigorösa
    metod som alla andra features, inte en särbehandling. Point-in-time:
    percentilrankningen är alltid mot samma veckas tvärsnitt.

    ``exclude_already_visible=True`` sätter NaN (inte cap) på redan-synligt-
    spärrade rader istället för att capa dem — svarar på "är edgen i botten
    bara spärren som gör sitt jobb, eller finns den även bland de OSPÄRRADE
    bolagen?" (Jonas, 2026-09-19, uppföljning på det första E1-svepet).
    """
    cfg = setup_score_config()
    w = cfg["weights"]
    df = wide[["obs_date"]].copy()

    def rank_pct(col: str, ascending: bool = True) -> pd.Series:
        if col not in wide.columns:
            return pd.Series(np.nan, index=wide.index)
        return wide.groupby("obs_date")[col].rank(pct=True, ascending=ascending) * 100.0

    volym = pd.concat([rank_pct("rvol_5_60"), rank_pct("vol_accel")], axis=1).mean(axis=1)
    attn = pd.concat([rank_pct("search_accel"), rank_pct("forum_accel")], axis=1).mean(axis=1)

    df["_abs_r1"] = wide["ret_1m"].abs() if "ret_1m" in wide else np.nan
    df["_abs_r3"] = wide["ret_3m"].abs() if "ret_3m" in wide else np.nan
    lugn = pd.concat(
        [
            df.groupby("obs_date")["_abs_r1"].rank(pct=True, ascending=False) * 100.0,
            df.groupby("obs_date")["_abs_r3"].rank(pct=True, ascending=False) * 100.0,
        ],
        axis=1,
    ).mean(axis=1)

    dist = wide["dist_52w_high"] if "dist_52w_high" in wide else pd.Series(np.nan, index=wide.index)
    d = (-dist.clip(upper=0.0)).fillna(np.nan)
    peak = cfg["coiled_zone"]["peak_distance"]
    zero_beyond = cfg["coiled_zone"]["zero_beyond_distance"]
    span = zero_beyond - peak
    coiled = pd.Series(0.0, index=wide.index)
    near = d <= peak
    mid = (d > peak) & (d <= zero_beyond)
    coiled[near] = (d[near] / peak).clip(lower=0) * 100.0 if peak else 0.0
    coiled[mid] = (((zero_beyond - d[mid]) / span).clip(lower=0) * 100.0) if span else 0.0
    coiled[dist.isna()] = np.nan

    comps = {
        "volym_uppbyggnad": volym.fillna(50.0),
        "uppmarksamhet": attn.fillna(50.0),
        "lugn_kurs": lugn.fillna(50.0),
        "coiled_zon": coiled.fillna(50.0),
    }
    wsum = sum(w.values())
    total = sum(comps[k] * w[k] for k in comps) / wsum

    gate = cfg["already_visible_gate"]
    r3m = wide["ret_3m"] if "ret_3m" in wide else pd.Series(np.nan, index=wide.index)
    already_visible = (dist >= gate["dist_52w_high_min"]) & (r3m >= gate["ret_3m_min"])
    visible_mask = already_visible.fillna(False)

    if exclude_already_visible:
        total = total.where(~visible_mask)
        return total.round(1).rename("setup_score_ungated")

    total = total.where(~visible_mask, np.minimum(total, float(gate["capped_score"])))
    return total.round(1).rename("setup_score")


def _zone_phrase(dist: float | None) -> str:
    if dist is None:
        return "okänt läge mot årshögsta"
    if dist >= -0.06:
        return "vid årshögsta — redan synligt för alla, inget övertag här"
    return f"{abs(dist) * 100:.0f} % under årshögsta"
