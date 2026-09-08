"""Universe / panel integrity (integration — uses the ``pipeline_db`` fixture)."""

from __future__ import annotations

from marc.reference.universe import cap_segment


def test_cap_segment_boundary() -> None:
    assert cap_segment(1.7e9, 1.7e9) == "small"
    assert cap_segment(1.7e9 + 1, 1.7e9) == "mid"


def test_no_observation_before_min_history(pipeline_db) -> None:
    bad = pipeline_db.execute(
        """
        SELECT count(*) FROM observation o
        JOIN (SELECT security_id, min(session_date) d0 FROM price_daily GROUP BY 1) f USING (security_id)
        WHERE o.obs_date < f.d0 + INTERVAL 251 DAY
        """
    ).fetchone()[0]
    assert bad == 0


def test_delisted_names_have_no_observations_after_delisting(pipeline_db) -> None:
    bad = pipeline_db.execute(
        """
        SELECT count(*) FROM observation o
        JOIN security s USING (security_id)
        WHERE s.status <> 'listed' AND s.status_date IS NOT NULL
          AND o.obs_date > s.status_date
        """
    ).fetchone()[0]
    assert bad == 0


def test_membership_asof_is_pointintime(pipeline_db) -> None:
    # a member on date d must have valid_from <= d < valid_to (or open)
    bad = pipeline_db.execute(
        """
        SELECT count(*) FROM observation o
        WHERE o.in_universe AND NOT EXISTS (
            SELECT 1 FROM universe_membership m
            WHERE m.universe_name = o.universe_name
              AND m.security_id = o.security_id
              AND m.valid_from <= o.obs_date
              AND (m.valid_to IS NULL OR m.valid_to > o.obs_date)
        )
        """
    ).fetchone()[0]
    assert bad == 0


def test_cap_segment_matches_market_cap(pipeline_db) -> None:
    df = pipeline_db.execute(
        "SELECT cap_segment_at_entry, market_cap_sek FROM observation"
    ).df()
    small = df[df["cap_segment_at_entry"] == "small"]
    mid = df[df["cap_segment_at_entry"] == "mid"]
    assert (small["market_cap_sek"] <= 1.7e9 + 1).all()
    assert (mid["market_cap_sek"] > 1.7e9).all()


def test_targets_have_sane_range(pipeline_db) -> None:
    lo, hi = pipeline_db.execute(
        "SELECT min(value), max(value) FROM target_panel WHERE target_name = 'fwd_ret_90'"
    ).fetchone()
    assert lo >= -1.0000001
    assert hi < 50  # no runaway offer-price bug
