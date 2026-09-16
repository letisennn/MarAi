"""Insiderhandel (FI:s PDMR-register) + blankning (FI:s blankningsregister) —
manuellt exporterade filer, inte en automatiserad pull.

Godkänt 2026-09-16 (Jonas). Båda registren är gratis och öppna (FI kräver bara
källhänvisning), men publiceras via sökportaler (marknadssok.fi.se) utan en
dokumenterad bulk-API för automatiserad hämtning. Mönstret här är därför:
ladda ner en Excel/CSV-export från portalens egen exportfunktion, spara den
lokalt, och kör ``marc ingest insider <fil>`` / ``marc ingest short-interest
<fil>``. Kolumnnamnen nedan är satta efter FI:s dokumenterade fält och MAR
artikel 19-standardmallen (PDMR) — **inte verifierade mot en riktig export
än**. Om en riktig fil har andra kolumnnamn ger ``_find_col`` ett tydligt fel
som listar vilka kolumner som faktiskt finns, så mappningen går snabbt att
justera.

Bolagsmatchning är namnbaserad (registret har inga ISIN i exportformatet i
den dokumentation som funnits tillgänglig) — normaliserad exakt-matchning mot
``security.name``, oidentifierade rader hoppas över och räknas som avvisade
(precis som prisingestionens ISIN-join).
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

from marc.config import get_logger

log = get_logger(__name__)

_BUY_WORDS = ("förvärv", "köp", "acquisition", "purchase", "buy")
_SELL_WORDS = ("avyttr", "försälj", "disposal", "sale", "sell")


def _find_col(df: pd.DataFrame, *keywords: str, required: bool = True) -> str | None:
    """Case-okänslig substrängsökning bland kolumnnamnen. Första träff vinner."""
    cols = list(df.columns)
    low = {c: str(c).lower() for c in cols}
    for kw in keywords:
        for c in cols:
            if kw.lower() in low[c]:
                return c
    if required:
        raise ValueError(
            f"hittar ingen kolumn som matchar {keywords!r}. Kolumner i filen: {cols}. "
            "Justera _find_col-anropen i marc.ingestion.insider_short mot den riktiga exporten."
        )
    return None


def _normalize_name(name: str) -> str:
    n = str(name).lower().strip()
    n = re.sub(r"\(publ\.?\)", "", n)
    n = re.sub(r"\bab\b", "", n)
    n = re.sub(r"[^a-zåäö0-9]+", "", n)
    return n


def _read_any(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p)
    return pd.read_csv(p, sep=None, engine="python")


def _security_map(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    sec = con.execute("SELECT security_id, name FROM security").df()
    return {_normalize_name(n): int(sid) for sid, n in zip(sec["security_id"], sec["name"], strict=False)}


def load_insider_export(con: duckdb.DuckDBPyConnection, path: str | Path) -> dict:
    """Läs in en PDMR-export (Excel/CSV från marknadssok.fi.se) i insider_transaction."""
    df = _read_any(path)
    if df.empty:
        return {"rows": 0, "rejected": 0}

    col_issuer = _find_col(df, "emittent", "issuer", "bolag")
    col_person = _find_col(df, "person", "namn")
    col_role = _find_col(df, "befattning", "role", required=False)
    col_kind = _find_col(df, "karaktär", "nature", "typ")
    col_date = _find_col(df, "transaktionsdatum", "transaction date")
    col_pub = _find_col(df, "publicer", "publication", required=False)
    col_instr = _find_col(df, "instrument", required=False)
    col_volume = _find_col(df, "volym", "volume")
    col_price = _find_col(df, "pris", "price", required=False)
    col_ccy = _find_col(df, "valuta", "currency", required=False)

    namemap = _security_map(con)
    rows, rejected = [], 0
    for _, r in df.iterrows():
        sid = namemap.get(_normalize_name(r[col_issuer]))
        if sid is None:
            rejected += 1
            continue
        kind = str(r[col_kind]).lower()
        ttype = "buy" if any(w in kind for w in _BUY_WORDS) else (
            "sell" if any(w in kind for w in _SELL_WORDS) else "other"
        )
        vol = pd.to_numeric(r.get(col_volume), errors="coerce")
        price = pd.to_numeric(r.get(col_price), errors="coerce") if col_price else None
        rows.append({
            "security_id": sid,
            "person_name": str(r[col_person]),
            "role": str(r[col_role]) if col_role else None,
            "transaction_date": pd.to_datetime(r[col_date], errors="coerce"),
            "publication_date": pd.to_datetime(r[col_pub], errors="coerce") if col_pub else None,
            "instrument_type": str(r[col_instr]) if col_instr else None,
            "transaction_type": ttype,
            "volume": None if pd.isna(vol) else float(vol),
            "price": None if price is None or pd.isna(price) else float(price),
            "currency": str(r[col_ccy]) if col_ccy else None,
            "amount_sek": (float(vol) * float(price)) if pd.notna(vol) and price is not None and pd.notna(price) else None,
        })
    out = pd.DataFrame(rows).dropna(subset=["transaction_date"])
    if out.empty:
        return {"rows": 0, "rejected": rejected}

    con.register("ins_df", out)
    con.execute(
        """
        INSERT OR REPLACE INTO insider_transaction
        (security_id, person_name, role, transaction_date, publication_date, instrument_type,
         transaction_type, volume, price, currency, amount_sek, source)
        SELECT security_id, person_name, role, transaction_date, publication_date, instrument_type,
               transaction_type, volume, price, currency, amount_sek, 'fi_pdmr_manual_export'
        FROM ins_df
        """
    )
    con.unregister("ins_df")
    log.info("insider: %d rader inlästa, %d avvisade (bolag ej matchat)", len(out), rejected)
    return {"rows": len(out), "rejected": rejected}


def load_short_interest_export(con: duckdb.DuckDBPyConnection, path: str | Path) -> dict:
    """Läs in en blankningsregister-export (aggregerade positioner) i short_interest."""
    df = _read_any(path)
    if df.empty:
        return {"rows": 0, "rejected": 0}

    col_issuer = _find_col(df, "emittent", "issuer", "bolag")
    col_date = _find_col(df, "positionsdatum", "position date", "datum")
    col_pct = _find_col(df, "procent", "percent", "%")

    namemap = _security_map(con)
    rows, rejected = [], 0
    for _, r in df.iterrows():
        sid = namemap.get(_normalize_name(r[col_issuer]))
        if sid is None:
            rejected += 1
            continue
        pct = pd.to_numeric(r.get(col_pct), errors="coerce")
        d = pd.to_datetime(r[col_date], errors="coerce")
        if pd.isna(pct) or pd.isna(d):
            rejected += 1
            continue
        rows.append({"security_id": sid, "position_date": d.date(), "pct_of_shares": float(pct)})
    out = pd.DataFrame(rows)
    if out.empty:
        return {"rows": 0, "rejected": rejected}

    con.register("short_df", out)
    con.execute(
        """
        INSERT OR REPLACE INTO short_interest (security_id, position_date, pct_of_shares, source)
        SELECT security_id, position_date, pct_of_shares, 'fi_blankning_manual_export' FROM short_df
        """
    )
    con.unregister("short_df")
    log.info("short interest: %d rader inlästa, %d avvisade (bolag ej matchat)", len(out), rejected)
    return {"rows": len(out), "rejected": rejected}
