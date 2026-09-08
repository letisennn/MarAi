"""Preliminär composite-score (handsatta vikter, ovaliderad).

Se ``composite.assess``. Får bara visas i appen med etiketten
"preliminär — ovaliderade vikter" och bredvid basnivån (CLAUDE.md regel 1–2).
"""

from marc.score.composite import ScoreBreakdown, assess

__all__ = ["ScoreBreakdown", "assess"]
