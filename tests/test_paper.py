"""Pappershandel: kontoräkning (kassa, snittkostnad, realiserad/orealiserad
P&L) och att den lever i en helt separat databasfil."""

from __future__ import annotations

import pandas as pd
import pytest

import marc.paper as paper


@pytest.fixture()
def isolated_paper_db(tmp_path, monkeypatch):
    monkeypatch.setenv("MARC_DATA_DIR", str(tmp_path))
    from marc import config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def test_paper_db_is_separate_from_research_db(isolated_paper_db) -> None:
    from marc.config import get_settings

    s = get_settings()
    assert s.paper_db_path != s.abs_db_path
    assert s.paper_db_path.name == "paper_trades.duckdb"


def test_default_account_has_default_capital(isolated_paper_db) -> None:
    with paper.session() as con:
        acct = paper.get_account(con)
    assert acct["starting_capital"] == paper.DEFAULT_STARTING_CAPITAL


def test_buy_reduces_cash_and_creates_position(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, security_id=1, side="buy", shares=10, price_sek=100.0)
        summary = paper.account_summary(con, latest_prices={1: 120.0})
    assert summary["cash"] == pytest.approx(paper.DEFAULT_STARTING_CAPITAL - 1000.0)
    assert len(summary["positions"]) == 1
    pos = summary["positions"].iloc[0]
    assert pos["shares"] == 10
    assert pos["avg_cost"] == pytest.approx(100.0)
    assert pos["market_value"] == pytest.approx(1200.0)
    assert pos["unrealized_pnl"] == pytest.approx(200.0)
    assert summary["total_value"] == pytest.approx(paper.DEFAULT_STARTING_CAPITAL + 200.0)


def test_average_cost_and_realized_pnl_on_partial_sell(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, 1, "buy", 10, 100.0)
        paper.record_trade(con, 1, "buy", 10, 200.0)   # avg cost now 150
        paper.record_trade(con, 1, "sell", 5, 180.0)   # realize 5*(180-150)=150
        summary = paper.account_summary(con, latest_prices={1: 150.0})
    pos = summary["positions"].iloc[0]
    assert pos["shares"] == 15
    assert pos["avg_cost"] == pytest.approx(150.0)
    assert summary["realized_pnl"] == pytest.approx(150.0)


def test_cannot_oversell_position(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, 1, "buy", 5, 100.0)
        paper.record_trade(con, 1, "sell", 100, 100.0)  # säljer mer än man äger
        trades = paper.list_trades(con)
        pos = paper.compute_positions(trades)
    assert pos.iloc[0]["shares"] == pytest.approx(0.0)  # klampad, inte negativ


def test_reset_account_clears_trades_and_sets_new_capital(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, 1, "buy", 1, 50.0)
        paper.reset_account(con, starting_capital=50_000.0)
        trades = paper.list_trades(con)
        acct = paper.get_account(con)
    assert trades.empty
    assert acct["starting_capital"] == 50_000.0


def test_invalid_side_and_nonpositive_amounts_rejected(isolated_paper_db) -> None:
    with paper.session() as con:
        with pytest.raises(ValueError):
            paper.record_trade(con, 1, "hold", 1, 100.0)
        with pytest.raises(ValueError):
            paper.record_trade(con, 1, "buy", 0, 100.0)
        with pytest.raises(ValueError):
            paper.record_trade(con, 1, "buy", 1, -5.0)


def test_trades_with_pnl_marks_buys_none_and_sells_with_pct(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, 1, "buy", 10, 100.0)
        paper.record_trade(con, 1, "buy", 10, 200.0)   # avg cost 150
        paper.record_trade(con, 1, "sell", 5, 180.0)   # +20% mot snittkostnaden
        trades = paper.list_trades(con)
    out = paper.trades_with_pnl(trades)
    buys = out[out["side"] == "buy"]
    sells = out[out["side"] == "sell"]
    assert buys["realized_pnl"].isna().all()
    assert buys["realized_pnl_pct"].isna().all()
    assert sells.iloc[0]["realized_pnl"] == pytest.approx(150.0)
    assert sells.iloc[0]["realized_pnl_pct"] == pytest.approx(0.2)


def test_compute_positions_empty_trades_returns_empty_frame() -> None:
    out = paper.compute_positions(pd.DataFrame())
    assert out.empty
    assert list(out.columns) == ["security_id", "shares", "avg_cost", "cost_basis", "realized_pnl"]
