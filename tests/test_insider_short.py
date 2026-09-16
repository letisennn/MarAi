"""Insider-/blankningsparsern (marc.ingestion.insider_short): namnmatchning,
köp/sälj-klassificering, avvisade rader vid omatchat bolag. Ren funktion av en
liten temp-fil, ingen nätåtkomst."""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from marc.db import run_migrations
from marc.ingestion.insider_short import load_insider_export, load_short_interest_export


@pytest.fixture()
def db(tmp_path):
    con = duckdb.connect(str(tmp_path / "t.duckdb"))
    run_migrations(con)
    con.execute(
        "INSERT INTO security (isin, name, country, currency) VALUES "
        "('SE0001', 'Stille AB', 'SE', 'SEK'), "
        "('SE0002', 'Rejlers AB (publ)', 'SE', 'SEK')"
    )
    yield con
    con.close()


def test_insider_export_matches_by_normalized_name_and_classifies_side(db, tmp_path) -> None:
    df = pd.DataFrame({
        "Emittent": ["Stille AB", "Rejlers AB (publ)", "Okänt Bolag AB"],
        "Person i ledande ställning": ["Anna Andersson", "Bo Bengtsson", "Ola Nordmann"],
        "Karaktär": ["Förvärv", "Avyttring", "Förvärv"],
        "Transaktionsdatum": ["2026-06-01", "2026-06-02", "2026-06-03"],
        "Publiceringsdatum": ["2026-06-03", "2026-06-04", "2026-06-05"],
        "Volym": [100, 50, 10],
        "Pris": [200.0, 300.0, 10.0],
        "Valuta": ["SEK", "SEK", "SEK"],
    })
    p = tmp_path / "pdmr.csv"
    df.to_csv(p, index=False)

    out = load_insider_export(db, p)
    assert out["rows"] == 2
    assert out["rejected"] == 1  # "Okänt Bolag AB" matchar inget

    rows = db.execute(
        "SELECT security_id, transaction_type, amount_sek FROM insider_transaction ORDER BY security_id"
    ).df()
    assert set(rows["transaction_type"]) == {"buy", "sell"}
    assert rows.loc[rows["transaction_type"] == "buy", "amount_sek"].iloc[0] == pytest.approx(100 * 200.0)


def test_short_interest_export_matches_and_stores_pct(db, tmp_path) -> None:
    df = pd.DataFrame({
        "Emittentens namn": ["Stille AB", "Ej Matchat AB"],
        "Positionsdatum": ["2026-06-10", "2026-06-10"],
        "Position i procent": [1.25, 2.0],
    })
    p = tmp_path / "short.csv"
    df.to_csv(p, index=False)

    out = load_short_interest_export(db, p)
    assert out["rows"] == 1
    assert out["rejected"] == 1

    row = db.execute("SELECT pct_of_shares FROM short_interest").fetchone()
    assert row[0] == pytest.approx(1.25)


def test_missing_required_column_raises_clear_error(db, tmp_path) -> None:
    df = pd.DataFrame({"Bolagsnamn": ["Stille AB"], "Datum": ["2026-06-01"]})
    p = tmp_path / "bad.csv"
    df.to_csv(p, index=False)
    with pytest.raises(ValueError, match="hittar ingen kolumn"):
        load_short_interest_export(db, p)
