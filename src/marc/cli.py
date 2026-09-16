"""``marc`` command-line interface (Typer)."""

from __future__ import annotations

import json

import typer

from marc.config import get_logger

app = typer.Typer(add_completion=False, help="Noel AI — Nordic small-cap discovery engine")
db_app = typer.Typer(help="database")
app.add_typer(db_app, name="db")
disc_app = typer.Typer(help="discovery log / paper trading")
app.add_typer(disc_app, name="discovery")
ingest_app = typer.Typer(help="manuellt exporterade register (insider, blankning)")
app.add_typer(ingest_app, name="ingest")

log = get_logger("marc.cli")


@db_app.command("migrate")
def db_migrate() -> None:
    """Apply pending SQL migrations."""
    from marc.db import run_migrations
    from marc.db.session import session

    with session(read_only=False) as con:
        applied = run_migrations(con)
    typer.echo(f"applied: {applied or 'none'}")


@app.command("pipeline")
def pipeline(
    source: str = typer.Option("synthetic", help="synthetic | yfinance"),
    reset: bool = typer.Option(False, "--reset", help="delete the database first"),
    attention_source: str = typer.Option(
        "synthetic", "--attention-source",
        help="synthetic | real (riktig Trends + nyheter; långsamt, flera minuter för hela universumet)",
    ),
) -> None:
    """Run the full v0.1 pipeline end-to-end."""
    from marc.pipeline import run_all

    summary = run_all(source=source, reset=reset, attention_source=attention_source)
    typer.echo(json.dumps(summary, indent=2, default=str))


@app.command("panel")
def panel_build() -> None:
    """Rebuild observation + feature_panel + target_panel."""
    from marc.db.session import session
    from marc.panel import build_panel

    with session(read_only=False) as con:
        typer.echo(json.dumps(build_panel(con), indent=2, default=str))


@app.command("stats")
def stats_e1() -> None:
    """Run experiment E1 (base rates, univariate IC, Fama-MacBeth)."""
    from marc.db.session import session
    from marc.stats import run_experiment_e1

    with session(read_only=False) as con:
        typer.echo(json.dumps(run_experiment_e1(con), indent=2, default=str))


@app.command("signals")
def signals_run() -> None:
    """Apply the pre-registered E1d rules and record outcomes."""
    from marc.db.session import session
    from marc.signals import apply_rules

    with session(read_only=False) as con:
        typer.echo(json.dumps(apply_rules(con), indent=2, default=str))


@disc_app.command("snapshot")
def discovery_snapshot(
    top: int = typer.Option(10, help="antal kandidater att spara"),
    segment: str = typer.Option("small", help="small | mid | all"),
) -> None:
    """Spara dagens radar-kandidater som discovery-rader (point-in-time)."""
    from marc.db.session import session
    from marc.discovery.snapshot import snapshot

    with session(read_only=False) as con:
        typer.echo(json.dumps(snapshot(con, top=top, segment=segment), indent=2, default=str))


@disc_app.command("evaluate")
def discovery_evaluate() -> None:
    """Fyll i utfall (+1/5/20/30/60/90/180 d) för discoveries vars horisont passerat."""
    from marc.db.session import session
    from marc.discovery.snapshot import evaluate

    with session(read_only=False) as con:
        typer.echo(json.dumps(evaluate(con), indent=2, default=str))


@ingest_app.command("insider")
def ingest_insider(file: str = typer.Argument(..., help="Excel/CSV-export från FI:s PDMR-register")) -> None:
    """Läs in en manuellt nedladdad PDMR-export (insiderhandel)."""
    from marc.db.session import session
    from marc.ingestion.insider_short import load_insider_export

    with session(read_only=False) as con:
        typer.echo(json.dumps(load_insider_export(con, file), indent=2, default=str))


@ingest_app.command("short-interest")
def ingest_short_interest(
    file: str = typer.Argument(..., help="Excel/CSV-export från FI:s blankningsregister"),
) -> None:
    """Läs in en manuellt nedladdad blankningsregister-export."""
    from marc.db.session import session
    from marc.ingestion.insider_short import load_short_interest_export

    with session(read_only=False) as con:
        typer.echo(json.dumps(load_short_interest_export(con, file), indent=2, default=str))


@app.command("llm-narrative")
def llm_narrative(
    company: str = typer.Argument(..., help="Bolagsnamn (som i security.name)"),
    days: int = typer.Option(21, help="hur många dagars rubriker att titta på"),
) -> None:
    """Klassificera ett bolags senaste nyhetsrubriker med Claude (kräver ANTHROPIC_API_KEY).

    Undantag från CLAUDE.md regel 4 (Jonas, 2026-09-16). Kostar riktiga pengar
    per anrop. Inga kvantitativa påståenden begärs eller accepteras — bara
    sentiment/tema-klassificering av rubriktext.
    """
    from marc.llm import classify_narrative_for_company

    result = classify_narrative_for_company(company, days=days)
    typer.echo(json.dumps(result.__dict__, indent=2, ensure_ascii=False))


@app.command("info")
def info() -> None:
    """Show row counts for the main tables."""
    from marc.db.session import session

    tables = ["security", "price_daily", "universe_membership", "observation",
              "feature_panel", "target_panel", "experiment_result", "signal_log", "signal_outcome"]
    with session(read_only=True) as con:
        for t in tables:
            try:
                n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            except Exception:  # noqa: BLE001
                n = "-"
            typer.echo(f"{t:22s} {n}")


if __name__ == "__main__":
    app()
