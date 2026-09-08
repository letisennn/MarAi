# data/ (gitignored)

- `marc.duckdb`   — the database (curated tables).
- `raw/`          — immutable source dumps as Parquet/JSON, keyed by vintage_id.
                    Never edited; curated tables are rebuilt from here.
- `interim/`      — scratch intermediates, safe to delete.
- `analytical/`   — optional Parquet exports of panels for fast re-analysis.
- `seed/`         — the curated seed security list (checked in separately if small).

Nothing in here is committed except this README.
