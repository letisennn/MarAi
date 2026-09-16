"""Nyckelordsbaserad nyhetssentiment — ren funktion, ingen nätåtkomst.
Ingen LLM (CLAUDE.md regel 4): bara räkning av positiva/negativa svenska
finansord i rubriktext."""

from __future__ import annotations

from marc.ingestion.news_source import _keyword_sentiment


def test_empty_titles_returns_none() -> None:
    assert _keyword_sentiment([]) is None


def test_no_keyword_hits_returns_zero() -> None:
    assert _keyword_sentiment(["Bolaget håller årsstämma i maj"]) == 0.0


def test_positive_keywords_score_positive() -> None:
    s = _keyword_sentiment(["Bolaget rusar efter rekordvinst", "Vinner stororder i Tyskland"])
    assert s is not None and s > 0


def test_negative_keywords_score_negative() -> None:
    s = _keyword_sentiment(["Bolaget rasar efter vinstvarning", "Nyemission väntas späda ut aktien"])
    assert s is not None and s < 0


def test_mixed_keywords_stay_within_bounds() -> None:
    s = _keyword_sentiment(["Rusar på rekordvinst", "Rasar efter vinstvarning"])
    assert s is not None and -1.0 <= s <= 1.0
