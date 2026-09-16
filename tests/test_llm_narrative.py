"""marc.llm.narrative: prompt-/svarshantering, ingen riktig nätåtkomst.
Anthropic-klienten mockas — det här är plumbing-tester, inte ett test av
modellens faktiska omdöme."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from marc.llm.narrative import _parse_json, classify_narrative


def test_missing_api_key_raises_clear_error(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        classify_narrative("Testbolaget AB", ["En rubrik"])


def test_empty_headlines_rejected() -> None:
    with pytest.raises(ValueError, match="inga rubriker"):
        classify_narrative("Testbolaget AB", [])


def test_parse_json_handles_fenced_code_block() -> None:
    raw = '```json\n{"sentiment_label": "positiv", "sentiment_score": 0.4, ' \
          '"theme": "stororder", "reasoning": "vann ett kontrakt"}\n```'
    data = _parse_json(raw)
    assert data["sentiment_label"] == "positiv"


def test_parse_json_raises_on_garbage() -> None:
    with pytest.raises(ValueError, match="kunde inte tolka"):
        _parse_json("det här är inte json")


def test_classify_narrative_calls_model_and_clamps_score(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    payload = {
        "sentiment_label": "starkt positiv", "sentiment_score": 5.0,  # ska klampas till 1.0
        "theme": "rekordvinst", "reasoning": "bolaget slog förväntningarna",
    }
    fake_response = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(payload))])
    fake_client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: fake_response))

    with patch("anthropic.Anthropic", return_value=fake_client) as mock_ctor:
        result = classify_narrative("Testbolaget AB", ["Testbolaget slår förväntningarna", "Rekordvinst för Q3"])

    mock_ctor.assert_called_once_with(api_key="test-key")
    assert result.sentiment_label == "starkt positiv"
    assert result.sentiment_score == 1.0
    assert result.theme == "rekordvinst"
    assert result.n_headlines == 2
