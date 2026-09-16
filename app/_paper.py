"""Tunn Streamlit-wrapper mot ``marc.paper`` — pappershandel.

Enda stället i appen som skriver, och det skriver bara till en egen, separat
databasfil (``data/paper_trades.duckdb``) — aldrig till ``data/marc.duckdb``,
som resten av appen bara läser. Se ``marc.paper`` för motivering och logik.
"""

from __future__ import annotations

import marc.paper as _paper


def summary(latest_prices: dict) -> dict:
    with _paper.session() as con:
        return _paper.account_summary(con, latest_prices)


def trades():
    with _paper.session() as con:
        return _paper.list_trades(con)


def buy(security_id: int, shares: float, price: float, note: str | None = None) -> int:
    with _paper.session() as con:
        return _paper.record_trade(con, security_id, "buy", shares, price, note=note)


def sell(security_id: int, shares: float, price: float, note: str | None = None) -> int:
    with _paper.session() as con:
        return _paper.record_trade(con, security_id, "sell", shares, price, note=note)


def reset(starting_capital: float = _paper.DEFAULT_STARTING_CAPITAL) -> None:
    with _paper.session() as con:
        _paper.reset_account(con, starting_capital)
