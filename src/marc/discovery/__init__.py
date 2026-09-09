"""Discovery-lagret — marknadsfas + historiska analoger.

Rena, reproducerbara funktioner ovanpå ``feature_panel`` / ``target_panel``.
Ingen skattad modell, inga framåtblickande features. Fasmodellen och
analog-motorn är **beskrivande verktyg** — de bevisar ingenting och ska visas
märkta som experimentella tills de testats kronologiskt out-of-sample.
"""

from marc.discovery.analogues import (
    ANALOGUE_FEATURES,
    ANALOGUE_FEATURES_ATTENTION,
    analogue_outcomes,
    find_analogues,
)
from marc.discovery.phase import PHASES, Phase, classify_phase

__all__ = [
    "ANALOGUE_FEATURES",
    "ANALOGUE_FEATURES_ATTENTION",
    "PHASES",
    "Phase",
    "analogue_outcomes",
    "classify_phase",
    "find_analogues",
]
