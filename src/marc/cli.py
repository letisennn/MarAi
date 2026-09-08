"""``marc`` command-line interface (Typer)."""

from __future__ import annotations

import json

import typer

from marc.config import get_logger

app = typer.Typer(add_completion=False, help="Marc AI — Nordic small-cap research engine (v0.1)")
db_app = typer.Typer(help="database")
app.add_typer(db_app, name="db")

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
) -> None:
    """Run the full v0.1 pipeline end-to-end."""
    from marc.pipeline import run_all

    summary = run_all(source=source, reset=reset)
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
