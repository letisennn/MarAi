"""Marknadsfas / hype-cykel — en beskrivande klassificering per observation.

Sju faser (spec-brief §10). Klassificeringen bygger på **förändringstakt** i
uppmärksamhet och handel före absolut nivå (§11). Ren funktion av de features
som var kända vid tidpunkten — inga targets, ingen framtida data.

Ingen fas betyder automatiskt köp eller sälj. Modellen är ett arbetsverktyg som
senare ska testas historiskt (klarar fas X att förutsäga rörelse Y out-of-sample?).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Phase:
    key: str
    idx: int          # 1..7 längs cykeln
    label: str
    marker: str       # kort neutral symbol (terminalkänsla, ingen 🚀-estetik)
    note: str          # klartext: vad som mäts, inte vad som "kommer att" hända


PHASES: list[Phase] = [
    Phase("low",          1, "Låg uppmärksamhet",   "·",
          "Normal eller låg handel, inget ökande intresse, kursen utan riktning."),
    Phase("early",        2, "Tidig upptäckt",      "→",
          "Handeln eller sökintresset har börjat ticka upp från en låg nivå, kursen har ännu inte dragit."),
    Phase("accelerating", 3, "Accelererande",       "↗",
          "Uppmärksamhet och volym ökar i takt, kursen har börjat röra sig uppåt."),
    Phase("hype",         4, "Snabb hype",          "↑",
          "Hög och stigande uppmärksamhet, kraftigt förhöjd volym, stark kursrörelse — nära årshögsta."),
    Phase("mass",         5, "Bred uppmärksamhet",  "=",
          "Uppmärksamheten är hög men ökar inte längre; kursen är utsträckt. De flesta känner redan till bolaget."),
    Phase("exhaustion",   6, "Avtagande hype",      "↘",
          "Uppmärksamheten faller tillbaka medan kursen börjar vända ner; svängningarna ökar."),
    Phase("reversal",     7, "Möjlig vändning ned", "↓",
          "Fallande intresse och kurs, en bit under årshögsta — ofta distribution efter en topp."),
]
_BY_KEY = {p.key: p for p in PHASES}

_UNKNOWN = Phase("unknown", 0, "Okänt läge", "?",
                 "För lite data för att placera bolaget i cykeln.")


def _f(feats: dict, name: str) -> float | None:
    v = feats.get(name)
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    return float(v)


def classify_phase(feats: dict) -> Phase:
    """Placera en observation i hype-cykeln utifrån dess kända features.

    Faller tillbaka på pris/volym om attention-features saknas (de är syntetiska
    i nuläget). Returnerar ``_UNKNOWN`` om även pris/volym saknas.
    """
    r1m = _f(feats, "ret_1m")
    r3m = _f(feats, "ret_3m")
    rvol = _f(feats, "rvol_5_60")
    vacc = _f(feats, "vol_accel")
    dist = _f(feats, "dist_52w_high")
    vexp = _f(feats, "vol_expansion")

    # attention (syntetisk just nu) — används om den finns, annars None
    a_lvl = np.nanmean([x for x in (_f(feats, "search_level_z"), _f(feats, "forum_buzz_z"),
                                    _f(feats, "news_rate_z")) if x is not None]) \
        if any(_f(feats, k) is not None for k in ("search_level_z", "forum_buzz_z", "news_rate_z")) else None
    a_acc = np.nanmean([x for x in (_f(feats, "search_accel"), _f(feats, "forum_accel")) if x is not None]) \
        if any(_f(feats, k) is not None for k in ("search_accel", "forum_accel")) else None

    if r1m is None and r3m is None and rvol is None:
        return _UNKNOWN

    r1m = r1m if r1m is not None else 0.0
    r3m = r3m if r3m is not None else 0.0
    rvol = rvol if rvol is not None else 1.0
    vacc = vacc if vacc is not None else 0.0
    dist = dist if dist is not None else -0.30
    vexp = vexp if vexp is not None else 1.0

    moving_up = r1m >= 0.04
    moving_up_hard = r1m >= 0.15
    falling = r1m <= -0.03
    extended = r3m >= 0.45
    at_high = dist >= -0.06
    off_high = dist <= -0.15

    vol_hot = rvol >= 2.5
    vol_warm = rvol >= 1.3
    # "ökar" = attention-acceleration om den finns, annars volymacceleration
    rising = (a_acc is not None and a_acc > 0.10) or vacc > 0
    cooling = (a_acc is not None and a_acc < -0.15) or (vacc < 0 and rvol < 1.2)
    attn_high = a_lvl is not None and a_lvl >= 1.5

    # ----- beslutsträd längs cykeln (första träff vinner) -----
    if falling and r3m < 0.0 and off_high and not rising:
        phase = _BY_KEY["reversal"]                                   # 7
    elif (cooling or (vacc < 0 and rvol < 1.2)) and r1m < 0.0 and r3m > 0.05 \
            and (vexp >= 1.15 or vol_warm):
        phase = _BY_KEY["exhaustion"]                                 # 6
    elif (attn_high or vol_hot) and not rising and extended and dist >= -0.12:
        phase = _BY_KEY["mass"]                                       # 5
    elif (attn_high or vol_hot) and (rising or moving_up_hard) and moving_up and dist >= -0.15:
        phase = _BY_KEY["hype"]                                       # 4
    elif (rising or vol_warm) and moving_up and r3m >= -0.05:
        phase = _BY_KEY["accelerating"]                               # 3
    elif (rising or vol_warm) and not at_high and r1m < 0.15:
        phase = _BY_KEY["early"]                                      # 2
    else:
        phase = _BY_KEY["low"]                                        # 1

    # skyddsnät: kraftigt förhöjd handel eller stark kursrörelse ska aldrig bli "låg"
    if phase.key == "low":
        if vol_hot:
            phase = _BY_KEY["accelerating"]
        elif moving_up_hard and not off_high:
            phase = _BY_KEY["early"]
    return phase
