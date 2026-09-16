"""Pappershandel — fejkat startkapital, riktiga kurser.

En helt separat DuckDB-fil (``data/paper_trades.duckdb``, se
``Settings.paper_db_path``), medvetet skild från ``data/marc.duckdb``: appen är
annars read-only mot forskningsdatabasen (CLAUDE.md), och en delad fil skulle
dessutom krocka med den read-only-anslutning som redan hålls öppen (DuckDB
tillåter inte en skrivbar anslutning samtidigt som en read-only-lås finns).
Det här är enda stället i hela projektet som skriver från appen — och det
skriver bara till användarens egen leklåda, aldrig till forskningsdata.

Snittkostnadsmetod (average cost): varje sälj realiserar vinst/förlust mot
positionens löpande snittkostnad; ingen FIFO/LIFO-bokföring. Enkelt och
tillräckligt för en pappersportfölj.
"""

from __future__ import annotations

import datetime as dt
from contextlib import contextmanager

import duckdb
import pandas as pd

from marc.config import get_settings

DEFAULT_STARTING_CAPITAL = 100_000.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    account_id INTEGER PRIMARY KEY,
    starting_capital_sek DOUBLE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE SEQUENCE IF NOT EXISTS trade_id_seq START 1;
CREATE TABLE IF NOT EXISTS trade (
    trade_id BIGINT PRIMARY KEY DEFAULT nextval('trade_id_seq'),
    security_id BIGINT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy','sell')),
    shares DOUBLE NOT NULL CHECK (shares > 0),
    price_sek DOUBLE NOT NULL CHECK (price_sek > 0),
    trade_date DATE NOT NULL,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
"""


@contextmanager
def session():
    """Kort anslutning, öppnas och stängs per operation — ingen delad, cachad
    skriv-anslutning som kan krocka med annat."""
    path = get_settings().paper_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        for stmt in _SCHEMA.strip().split(";"):
            if stmt.strip():
                con.execute(stmt)
        yield con
    finally:
        con.close()


def get_account(con: duckdb.DuckDBPyConnection) -> dict:
    row = con.execute(
        "SELECT starting_capital_sek, created_at FROM account WHERE account_id = 1"
    ).fetchone()
    if row is None:
        con.execute(
            "INSERT INTO account (account_id, starting_capital_sek) VALUES (1, ?)",
            [DEFAULT_STARTING_CAPITAL],
        )
        return {"starting_capital": DEFAULT_STARTING_CAPITAL, "created_at": None}
    return {"starting_capital": float(row[0]), "created_at": row[1]}


def reset_account(con: duckdb.DuckDBPyConnection, starting_capital: float = DEFAULT_STARTING_CAPITAL) -> None:
    con.execute("DELETE FROM trade")
    con.execute("DELETE FROM account")
    con.execute("INSERT INTO account (account_id, starting_capital_sek) VALUES (1, ?)", [starting_capital])


def record_trade(
    con: duckdb.DuckDBPyConnection,
    security_id: int,
    side: str,
    shares: float,
    price_sek: float,
    trade_date: dt.date | None = None,
    note: str | None = None,
) -> int:
    if side not in ("buy", "sell"):
        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
    if shares <= 0 or price_sek <= 0:
        raise ValueError("shares and price_sek must be positive")
    get_account(con)  # säkerställ att kontot finns
    con.execute(
        "INSERT INTO trade (security_id, side, shares, price_sek, trade_date, note) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [int(security_id), side, float(shares), float(price_sek),
         trade_date or dt.date.today(), note],
    )
    return int(con.execute("SELECT trade_id FROM trade ORDER BY trade_id DESC LIMIT 1").fetchone()[0])


def list_trades(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        "SELECT trade_id, security_id, side, shares, price_sek, trade_date, note, created_at "
        "FROM trade ORDER BY created_at, trade_id"
    ).df()
    return df


def compute_positions(trades: pd.DataFrame) -> pd.DataFrame:
    """En rad per bolag som handlats: kvarvarande antal, snittkostnad,
    kostnadsbas och realiserad vinst/förlust (snittkostnadsmetod)."""
    cols = ["security_id", "shares", "avg_cost", "cost_basis", "realized_pnl"]
    if trades.empty:
        return pd.DataFrame(columns=cols)
    out = []
    for sid, g in trades.sort_values(["trade_date", "created_at", "trade_id"]).groupby("security_id"):
        shares = 0.0
        cost = 0.0
        realized = 0.0
        for _, t in g.iterrows():
            if t["side"] == "buy":
                shares += t["shares"]
                cost += t["shares"] * t["price_sek"]
            else:
                if shares > 1e-9:
                    avg = cost / shares
                    sold = min(t["shares"], shares)  # skydd mot att sälja mer än man äger
                    realized += sold * (t["price_sek"] - avg)
                    shares -= sold
                    cost -= sold * avg
        out.append({
            "security_id": int(sid), "shares": shares,
            "avg_cost": (cost / shares) if shares > 1e-9 else None,
            "cost_basis": cost, "realized_pnl": realized,
        })
    return pd.DataFrame(out, columns=cols)


def trades_with_pnl(trades: pd.DataFrame) -> pd.DataFrame:
    """En rad per affär, i tidsordning, med — för sälj — realiserad vinst/förlust
    i kr och i procent mot den löpande snittkostnaden vid det tillfället. Köp
    får None (ingen vinst/förlust att visa förrän man säljer)."""
    if trades.empty:
        return trades.assign(realized_pnl=pd.Series(dtype=float), realized_pnl_pct=pd.Series(dtype=float))
    rows = []
    for _, g in trades.sort_values(["trade_date", "created_at", "trade_id"]).groupby("security_id"):
        shares = 0.0
        cost = 0.0
        for _, t in g.iterrows():
            r = t.to_dict()
            if t["side"] == "buy":
                shares += t["shares"]
                cost += t["shares"] * t["price_sek"]
                r["realized_pnl"], r["realized_pnl_pct"] = None, None
            else:
                if shares > 1e-9:
                    avg = cost / shares
                    sold = min(t["shares"], shares)
                    r["realized_pnl"] = sold * (t["price_sek"] - avg)
                    r["realized_pnl_pct"] = (t["price_sek"] / avg - 1.0) if avg else None
                    shares -= sold
                    cost -= sold * avg
                else:
                    r["realized_pnl"], r["realized_pnl_pct"] = None, None
            rows.append(r)
    return pd.DataFrame(rows).sort_values(["trade_date", "created_at", "trade_id"]).reset_index(drop=True)


def account_summary(con: duckdb.DuckDBPyConnection, latest_prices: dict[int, float]) -> dict:
    """Kassa, positionsvärde, totalt värde och vinst/förlust mot startkapitalet."""
    acct = get_account(con)
    trades = list_trades(con)
    pos = compute_positions(trades)

    cash = acct["starting_capital"]
    for _, t in trades.iterrows():
        amt = float(t["shares"]) * float(t["price_sek"])
        cash += -amt if t["side"] == "buy" else amt

    open_pos = pos[pos["shares"] > 1e-9].copy()
    open_pos["price_now"] = open_pos["security_id"].map(latest_prices)
    open_pos["market_value"] = open_pos["shares"] * open_pos["price_now"]
    open_pos["unrealized_pnl"] = open_pos["market_value"] - open_pos["shares"] * open_pos["avg_cost"]

    positions_value = float(open_pos["market_value"].dropna().sum())
    unrealized = float(open_pos["unrealized_pnl"].dropna().sum())
    realized = float(pos["realized_pnl"].sum()) if not pos.empty else 0.0
    total_value = cash + positions_value
    starting = acct["starting_capital"]

    return {
        "starting_capital": starting,
        "cash": cash,
        "positions_value": positions_value,
        "total_value": total_value,
        "unrealized_pnl": unrealized,
        "realized_pnl": realized,
        "total_pnl": total_value - starting,
        "total_pnl_pct": (total_value - starting) / starting if starting else None,
        "positions": open_pos,
        "n_trades": int(len(trades)),
    }
