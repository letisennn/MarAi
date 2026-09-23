"""Statistical baseline — runs BEFORE any ML.

``run_experiment_e1`` (re)creates the E1 ``experiment`` row and writes all of
E1a (base rates), E1b (univariate IC / quintile sorts / event lift) and E1c
(Fama-MacBeth) results to ``experiment_result`` — including nulls.
Protocol: ``docs/methodology.md`` §3; pre-registration: ``docs/experiments/E1.md``.
"""

from __future__ import annotations

import json

import duckdb

from marc.config import get_logger, targets_config, universe_config
from marc.discovery.setup import compute_setup_score_panel
from marc.stats._panel import load_wide
from marc.stats.baseline import base_rates
from marc.stats.crosssection import fama_macbeth
from marc.stats.playbook import run_playbook
from marc.stats.univariate import univariate_sweep

log = get_logger(__name__)


def run_experiment_e1(con: duckdb.DuckDBPyConnection) -> dict:
    wide = load_wide(con)
    if wide.empty:
        raise RuntimeError("no panel data — run `marc panel build` first")
    # 2026-09-19 (Jonas): svep Uppbyggnadspoängen genom samma rigorösa E1-test
    # som alla andra features (rank-IC, kvintilspridning, kronologisk holdout)
    # istället för att bara lita på handsatta vikter och en enkel ja/nej-regel.
    wide["setup_score"] = compute_setup_score_panel(wide)
    # uppföljning: är bottenkvintilens underprestation bara spärren som gör
    # sitt jobb, eller finns edgen även bland de OSPÄRRADE bolagen? (NaN:ar
    # bort redan-synligt-bolagen istället för att capa dem.)
    wide["setup_score_ungated"] = compute_setup_score_panel(wide, exclude_already_visible=True)

    con.execute(
        """
        DELETE FROM experiment_result WHERE experiment_id IN
            (SELECT experiment_id FROM experiment WHERE name = 'E1')
        """
    )
    con.execute("DELETE FROM experiment WHERE name = 'E1'")

    spec = {
        "universe": universe_config()["universe_name"],
        "target_set_version": targets_config()["target_set_version"],
        "segment_filter": "small",
        "discovery_end": "2024-12-31",
        "holdout_start": "2025-01-01",
        "n_observations": int(len(wide)),
    }
    con.execute(
        """
        INSERT INTO experiment (name, hypothesis, prereg_doc, spec, status)
        VALUES ('E1', ?, 'docs/experiments/E1.md', ?, 'run')
        """,
        [
            "Does simple price/volume behaviour carry information about forward "
            "returns and large-move events in Nordic small-caps?",
            json.dumps(spec),
        ],
    )
    eid = con.execute("SELECT max(experiment_id) FROM experiment WHERE name = 'E1'").fetchone()[0]

    a = base_rates(con, eid, wide)
    b = univariate_sweep(con, eid, wide)
    c = fama_macbeth(con, eid, wide)
    d = run_playbook(con, eid, wide)

    n_res = con.execute(
        "SELECT count(*) FROM experiment_result WHERE experiment_id = ?", [eid]
    ).fetchone()[0]
    out = {"experiment_id": int(eid), "results_written": int(n_res),
           "base_rates_small": a, **b, **c, **d}
    log.info("E1 complete: %s", out)
    return out


__all__ = ["run_experiment_e1"]
