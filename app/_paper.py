"""Tunn Streamlit-wrapper mot ``marc.paper`` — pappershandel.

Enda stället i appen som skriver, och det skriver bara till en egen, separat
databasfil (``data/paper_trades.duckdb``) — aldrig till ``data/marc.duckdb``,
som resten av appen bara läser. Se ``marc.paper`` för motivering och logik.

Varje anrop tar ett ``owner`` ("jonas"/"hugo") — separata konton sedan
2026-09-19, se ``marc.paper`` för varför (ett delat konto lät en persons
nollställning radera den andras affärer).
"""

from __future__ import annotations

import marc.paper as _paper

OWNERS = _paper.OWNERS
DEFAULT_OWNER = _paper.DEFAULT_OWNER


def summary(owner: str, latest_prices: dict) -> dict:
    with _paper.session() as con:
        return _paper.account_summary(con, owner, latest_prices)


def trades(owner: str):
    with _paper.session() as con:
        return _paper.list_trades(con, owner)


def trades_with_pnl(trades_df):
    return _paper.trades_with_pnl(trades_df)


def buy(owner: str, security_id: int, shares: float, price: float,
        note: str | None = None, snapshot: dict | None = None) -> int:
    with _paper.session() as con:
        return _paper.record_trade(con, owner, security_id, "buy", shares, price, note=note, snapshot=snapshot)


def sell(owner: str, security_id: int, shares: float, price: float,
         note: str | None = None, snapshot: dict | None = None) -> int:
    with _paper.session() as con:
        return _paper.record_trade(con, owner, security_id, "sell", shares, price, note=note, snapshot=snapshot)


def set_note(owner: str, trade_id: int, note: str | None) -> bool:
    with _paper.session() as con:
        return _paper.set_trade_note(con, owner, trade_id, note)


def reset(owner: str, starting_capital: float = _paper.DEFAULT_STARTING_CAPITAL) -> None:
    with _paper.session() as con:
        _paper.reset_account(con, owner, starting_capital)
