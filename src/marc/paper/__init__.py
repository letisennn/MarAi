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

**Postgres-läge (2026-10-08, Jonas ville publicera utan egen server/kort).**
Vissa hostade miljöer (t.ex. Replits "Deployments") har INGEN beständig disk —
en lokal fil nollställs vid omdeploy, vilket hade raderat portföljerna. Om
miljövariabeln ``DATABASE_URL`` är satt pratar modulen istället med en riktig
Postgres-databas (t.ex. Replits inbyggda) via ``_PgConn`` nedan — en tunn
omslagsklass som efterliknar DuckDBs ``.execute(...).fetchone()/.fetchall()/
.df()``-API, så att alla funktioner nedan är identiska oavsett backend. Lokalt
(ingen ``DATABASE_URL``) är beteendet exakt som innan: samma DuckDB-fil."""

from __future__ import annotations

import datetime as dt
import json
import os
from contextlib import contextmanager

import duckdb
import pandas as pd

from marc.config import get_logger, get_settings

log = get_logger(__name__)

DEFAULT_STARTING_CAPITAL = 100_000.0

# 2026-09-19 (Jonas): var tidigare ETT delat konto för hela appen — en reset av
# vem som helst raderade båda personernas affärer. Nu ett konto PER ägare;
# reset_account() rör bara den ägarens rader. Se docs/data_sources.md.
OWNERS = ("jonas", "hugo")
DEFAULT_OWNER = "jonas"

# DOUBLE PRECISION (inte DuckDBs kortform DOUBLE) — DuckDB accepterar båda,
# riktig Postgres kräver långformen. Resten av schemat (SEQUENCE, nextval,
# ADD COLUMN IF NOT EXISTS, CHECK, now()) är identisk SQL i båda motorerna.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    account_id INTEGER PRIMARY KEY,
    starting_capital_sek DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE SEQUENCE IF NOT EXISTS trade_id_seq START 1;
CREATE TABLE IF NOT EXISTS trade (
    trade_id BIGINT PRIMARY KEY DEFAULT nextval('trade_id_seq'),
    security_id BIGINT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy','sell')),
    shares DOUBLE PRECISION NOT NULL CHECK (shares > 0),
    price_sek DOUBLE PRECISION NOT NULL CHECK (price_sek > 0),
    trade_date DATE NOT NULL,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
"""

# separat migreringssteg (inte i _SCHEMA ovan): lägger till `owner` på en fil
# som skapades innan per-person-konton fanns, utan att röra befintliga rader.
_MIGRATE_OWNER = """
ALTER TABLE account ADD COLUMN IF NOT EXISTS owner TEXT;
ALTER TABLE trade ADD COLUMN IF NOT EXISTS owner TEXT;
ALTER TABLE trade ADD COLUMN IF NOT EXISTS snapshot TEXT;
CREATE SEQUENCE IF NOT EXISTS account_id_seq START 2;
"""


class _PgResult:
    """Efterliknar DuckDBs resultatobjekt (.fetchone/.fetchall/.df) ovanpå en
    psycopg2-cursor, så anroparen inte behöver bry sig om vilken backend som
    används."""

    def __init__(self, cur) -> None:
        self._cur = cur

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def df(self) -> pd.DataFrame:
        cols = [d[0] for d in self._cur.description] if self._cur.description else []
        return pd.DataFrame(self._cur.fetchall(), columns=cols)


class _PgConn:
    """Tunn omslagsklass runt en psycopg2-anslutning med samma ytliga API som
    en duckdb-anslutning (``.execute(sql, params).fetchone()/.df()``), så att
    ingen av funktionerna nedanför i filen behöver veta vilken backend som
    används. DuckDBs ``?``-platshållare skrivs om till psycopg2:s ``%s``."""

    def __init__(self, raw) -> None:
        self._raw = raw

    def execute(self, sql: str, params=None) -> _PgResult:
        cur = self._raw.cursor()
        cur.execute(sql.replace("?", "%s"), params or None)
        return _PgResult(cur)

    def close(self) -> None:
        self._raw.close()


def _connect_postgres(dsn: str) -> _PgConn:
    import psycopg2  # lokal import: bara ett krav när DATABASE_URL faktiskt är satt

    raw = psycopg2.connect(dsn)
    raw.autocommit = True  # matchar DuckDB-filens beteende: varje statement slår igenom direkt
    return _PgConn(raw)


@contextmanager
def session():
    """Kort anslutning, öppnas och stängs per operation — ingen delad, cachad
    skriv-anslutning som kan krocka med annat.

    Om ``DATABASE_URL`` är satt (t.ex. Replits inbyggda Postgres) används den
    istället för en lokal fil — nödvändigt på hostade miljöer utan beständig
    disk, där en DuckDB-fil annars skulle nollställas vid varje omdeploy."""
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        con = _connect_postgres(dsn)
        log.info("paper: ansluter mot Postgres (DATABASE_URL satt)")
    else:
        path = get_settings().paper_db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(path))
    try:
        for stmt in _SCHEMA.strip().split(";"):
            if stmt.strip():
                con.execute(stmt)
        for stmt in _MIGRATE_OWNER.strip().split(";"):
            if stmt.strip():
                con.execute(stmt)
        # rader från innan ägarkolumnen fanns hörde till det enda kontot som
        # då fanns — det var Jonas som satte upp och testade funktionen.
        con.execute("UPDATE account SET owner = ? WHERE owner IS NULL", [DEFAULT_OWNER])
        con.execute("UPDATE trade SET owner = ? WHERE owner IS NULL", [DEFAULT_OWNER])
        yield con
    finally:
        con.close()


def _check_owner(owner: str) -> None:
    if owner not in OWNERS:
        raise ValueError(f"owner must be one of {OWNERS}, got {owner!r}")


def get_account(con: duckdb.DuckDBPyConnection, owner: str = DEFAULT_OWNER) -> dict:
    _check_owner(owner)
    row = con.execute(
        "SELECT starting_capital_sek, created_at FROM account WHERE owner = ?", [owner]
    ).fetchone()
    if row is None:
        con.execute(
            "INSERT INTO account (account_id, starting_capital_sek, owner) "
            "VALUES (nextval('account_id_seq'), ?, ?)",
            [DEFAULT_STARTING_CAPITAL, owner],
        )
        return {"starting_capital": DEFAULT_STARTING_CAPITAL, "created_at": None}
    return {"starting_capital": float(row[0]), "created_at": row[1]}


def reset_account(
    con: duckdb.DuckDBPyConnection, owner: str = DEFAULT_OWNER,
    starting_capital: float = DEFAULT_STARTING_CAPITAL,
) -> None:
    """Nollställer ENDAST ``owner``s eget konto — rör aldrig den andra ägarens
    affärer (2026-09-19: det var precis det som gick fel med ett delat konto)."""
    _check_owner(owner)
    con.execute("DELETE FROM trade WHERE owner = ?", [owner])
    con.execute("DELETE FROM account WHERE owner = ?", [owner])
    con.execute(
        "INSERT INTO account (account_id, starting_capital_sek, owner) "
        "VALUES (nextval('account_id_seq'), ?, ?)",
        [starting_capital, owner],
    )


def record_trade(
    con: duckdb.DuckDBPyConnection,
    owner: str,
    security_id: int,
    side: str,
    shares: float,
    price_sek: float,
    trade_date: dt.date | None = None,
    note: str | None = None,
    snapshot: dict | str | None = None,
) -> int:
    """``note`` = användarens egen anteckning ("varför"). ``snapshot`` = en
    automatisk ögonblicksbild av läget när affären gjordes (fas, volym, Noels
    nyckeltal) — sparas som JSON så den visar vad som gällde DÅ, inte vad som
    gäller när man tittar senare (Jonas, 2026-09-23)."""
    _check_owner(owner)
    if side not in ("buy", "sell"):
        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
    if shares <= 0 or price_sek <= 0:
        raise ValueError("shares and price_sek must be positive")
    get_account(con, owner)  # säkerställ att kontot finns
    con.execute(
        "INSERT INTO trade (security_id, side, shares, price_sek, trade_date, note, owner, snapshot) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [int(security_id), side, float(shares), float(price_sek),
         trade_date or dt.date.today(), (note or "").strip() or None, owner,
         snapshot if isinstance(snapshot, str) or snapshot is None
         else json.dumps(snapshot, ensure_ascii=False, default=str)],
    )
    return int(con.execute("SELECT trade_id FROM trade ORDER BY trade_id DESC LIMIT 1").fetchone()[0])


def list_trades(con: duckdb.DuckDBPyConnection, owner: str = DEFAULT_OWNER) -> pd.DataFrame:
    _check_owner(owner)
    df = con.execute(
        "SELECT trade_id, security_id, side, shares, price_sek, trade_date, note, snapshot, created_at "
        "FROM trade WHERE owner = ? ORDER BY created_at, trade_id",
        [owner],
    ).df()
    return df


def set_trade_note(con: duckdb.DuckDBPyConnection, owner: str, trade_id: int, note: str | None) -> bool:
    """Skriver/ändrar anteckningen på en affär. Rör bara ``owner``s egna affärer —
    returnerar False (och ändrar inget) om affären tillhör någon annan."""
    _check_owner(owner)
    hit = con.execute(
        "SELECT count(*) FROM trade WHERE trade_id = ? AND owner = ?", [int(trade_id), owner]
    ).fetchone()[0]
    if not hit:
        return False
    con.execute(
        "UPDATE trade SET note = ? WHERE trade_id = ? AND owner = ?",
        [(note or "").strip() or None, int(trade_id), owner],
    )
    return True


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


def account_summary(
    con: duckdb.DuckDBPyConnection, owner: str, latest_prices: dict[int, float],
) -> dict:
    """Kassa, positionsvärde, totalt värde och vinst/förlust mot startkapitalet
    för EN ägares konto."""
    acct = get_account(con, owner)
    trades = list_trades(con, owner)
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
