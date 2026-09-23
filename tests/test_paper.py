"""Pappershandel: kontoräkning (kassa, snittkostnad, realiserad/orealiserad
P&L), att den lever i en helt separat databasfil, och att Jonas och Hugo har
helt separata konton (2026-09-19: ett delat konto lät en persons nollställning
radera den andras affärer — det får aldrig hända igen)."""

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
        acct = paper.get_account(con, "jonas")
    assert acct["starting_capital"] == paper.DEFAULT_STARTING_CAPITAL


def test_invalid_owner_rejected(isolated_paper_db) -> None:
    with paper.session() as con:
        with pytest.raises(ValueError):
            paper.get_account(con, "someone_else")
        with pytest.raises(ValueError):
            paper.record_trade(con, "someone_else", 1, "buy", 1, 100.0)
        with pytest.raises(ValueError):
            paper.reset_account(con, "someone_else")


def test_buy_reduces_cash_and_creates_position(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, "jonas", security_id=1, side="buy", shares=10, price_sek=100.0)
        summary = paper.account_summary(con, "jonas", latest_prices={1: 120.0})
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
        paper.record_trade(con, "jonas", 1, "buy", 10, 100.0)
        paper.record_trade(con, "jonas", 1, "buy", 10, 200.0)   # avg cost now 150
        paper.record_trade(con, "jonas", 1, "sell", 5, 180.0)   # realize 5*(180-150)=150
        summary = paper.account_summary(con, "jonas", latest_prices={1: 150.0})
    pos = summary["positions"].iloc[0]
    assert pos["shares"] == 15
    assert pos["avg_cost"] == pytest.approx(150.0)
    assert summary["realized_pnl"] == pytest.approx(150.0)


def test_cannot_oversell_position(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, "jonas", 1, "buy", 5, 100.0)
        paper.record_trade(con, "jonas", 1, "sell", 100, 100.0)  # säljer mer än man äger
        trades = paper.list_trades(con, "jonas")
        pos = paper.compute_positions(trades)
    assert pos.iloc[0]["shares"] == pytest.approx(0.0)  # klampad, inte negativ


def test_reset_account_clears_trades_and_sets_new_capital(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, "jonas", 1, "buy", 1, 50.0)
        paper.reset_account(con, "jonas", starting_capital=50_000.0)
        trades = paper.list_trades(con, "jonas")
        acct = paper.get_account(con, "jonas")
    assert trades.empty
    assert acct["starting_capital"] == 50_000.0


def test_owners_have_fully_separate_accounts(isolated_paper_db) -> None:
    """Kärnan i 2026-09-19-fixen: Jonas och Hugo får aldrig se eller påverka
    varandras affärer eller kapital."""
    with paper.session() as con:
        paper.record_trade(con, "jonas", 1, "buy", 10, 100.0)
        paper.record_trade(con, "hugo", 2, "buy", 5, 200.0)

        jonas_trades = paper.list_trades(con, "jonas")
        hugo_trades = paper.list_trades(con, "hugo")
        assert len(jonas_trades) == 1
        assert len(hugo_trades) == 1
        assert jonas_trades.iloc[0]["security_id"] == 1
        assert hugo_trades.iloc[0]["security_id"] == 2

        jonas_summary = paper.account_summary(con, "jonas", latest_prices={1: 100.0, 2: 200.0})
        hugo_summary = paper.account_summary(con, "hugo", latest_prices={1: 100.0, 2: 200.0})
        assert jonas_summary["cash"] == pytest.approx(paper.DEFAULT_STARTING_CAPITAL - 1000.0)
        assert hugo_summary["cash"] == pytest.approx(paper.DEFAULT_STARTING_CAPITAL - 1000.0)


def test_reset_one_owner_never_touches_the_other(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, "jonas", 1, "buy", 10, 100.0)
        paper.record_trade(con, "hugo", 2, "buy", 5, 200.0)

        paper.reset_account(con, "jonas", starting_capital=999.0)

        jonas_trades = paper.list_trades(con, "jonas")
        hugo_trades = paper.list_trades(con, "hugo")
        hugo_acct = paper.get_account(con, "hugo")
    assert jonas_trades.empty
    assert len(hugo_trades) == 1  # Hugos affär är orörd
    assert hugo_acct["starting_capital"] == paper.DEFAULT_STARTING_CAPITAL  # Hugos kapital är orört


def test_invalid_side_and_nonpositive_amounts_rejected(isolated_paper_db) -> None:
    with paper.session() as con:
        with pytest.raises(ValueError):
            paper.record_trade(con, "jonas", 1, "hold", 1, 100.0)
        with pytest.raises(ValueError):
            paper.record_trade(con, "jonas", 1, "buy", 0, 100.0)
        with pytest.raises(ValueError):
            paper.record_trade(con, "jonas", 1, "buy", 1, -5.0)


def test_trades_with_pnl_marks_buys_none_and_sells_with_pct(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, "jonas", 1, "buy", 10, 100.0)
        paper.record_trade(con, "jonas", 1, "buy", 10, 200.0)   # avg cost 150
        paper.record_trade(con, "jonas", 1, "sell", 5, 180.0)   # +20% mot snittkostnaden
        trades = paper.list_trades(con, "jonas")
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


def test_note_and_snapshot_are_stored_and_returned(isolated_paper_db) -> None:
    snap = {"fas": {"label": "Tidig"}, "volym": {"mot_normalt": 1.8}}
    with paper.session() as con:
        tid = paper.record_trade(con, "jonas", 1, "buy", 10, 100.0,
                                 note="  Volym stiger, kursen lugn  ", snapshot=snap)
        t = paper.list_trades(con, "jonas")
    row = t[t["trade_id"] == tid].iloc[0]
    assert row["note"] == "Volym stiger, kursen lugn"          # trimmad
    import json
    assert json.loads(row["snapshot"]) == snap


def test_blank_note_is_stored_as_null(isolated_paper_db) -> None:
    with paper.session() as con:
        paper.record_trade(con, "jonas", 1, "buy", 1, 10.0, note="   ")
        t = paper.list_trades(con, "jonas")
    assert pd.isna(t.iloc[0]["note"])


def test_set_trade_note_updates_only_own_trades(isolated_paper_db) -> None:
    with paper.session() as con:
        j = paper.record_trade(con, "jonas", 1, "buy", 1, 10.0, note="orig")
        h = paper.record_trade(con, "hugo", 2, "buy", 1, 10.0, note="hugos")
        assert paper.set_trade_note(con, "jonas", j, "ny anteckning") is True
        assert paper.set_trade_note(con, "jonas", h, "försök röra Hugos") is False   # inte hans
        jn = paper.list_trades(con, "jonas").iloc[0]["note"]
        hn = paper.list_trades(con, "hugo").iloc[0]["note"]
    assert jn == "ny anteckning"
    assert hn == "hugos"


def test_old_file_without_snapshot_column_is_migrated_in_place(isolated_paper_db) -> None:
    """En paper_trades.duckdb skapad innan noteringar fanns ska öppnas utan att
    tappa några affärer — kolumnen läggs bara till."""
    import duckdb

    from marc.config import get_settings

    path = get_settings().paper_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute("CREATE SEQUENCE trade_id_seq START 1")
    con.execute(
        "CREATE TABLE trade (trade_id BIGINT PRIMARY KEY DEFAULT nextval('trade_id_seq'), "
        "security_id BIGINT NOT NULL, side TEXT NOT NULL, shares DOUBLE NOT NULL, price_sek DOUBLE NOT NULL, "
        "trade_date DATE NOT NULL, note TEXT, created_at TIMESTAMP NOT NULL DEFAULT now())"
    )
    con.execute("INSERT INTO trade (security_id, side, shares, price_sek, trade_date) VALUES (7,'buy',5,20.0,'2026-09-16')")
    con.close()

    with paper.session() as con:
        t = paper.list_trades(con, "jonas")
    assert len(t) == 1
    assert pd.isna(t.iloc[0]["snapshot"])
