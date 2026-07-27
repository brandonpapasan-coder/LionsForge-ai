from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trend_client_forwards_bounded_filters_and_validation():
    source = (ROOT / "lib/roadmap-outcome-trends.ts").read_text()
    assert "/roadmap-outcome-trends" in source
    assert "/roadmap-outcome-trends/validate" in source
    for field in ("granularity", "range_start", "range_end", "template_slug", "reason_code", "outcome_status"):
        assert field in source
    assert "cache: \"no-store\"" in source
    assert "Authentication required" in source


def test_trend_interface_has_accessible_states_export_provenance_and_guardrails():
    source = (ROOT / "components/learner-roadmap-outcome-trends.tsx").read_text()
    for phrase in (
        "Roadmap outcome trend snapshots",
        "Filter roadmap outcome trend snapshots",
        "Loading roadmap outcome trend snapshots",
        "role=\"alert\"",
        "aria-live=\"polite\"",
        "Export deterministic trend JSON",
        "Validate current trend bundle",
        "Trend digest",
        "Source report digest",
        "statistics are hidden until this window has at least",
        "do not prove learning effectiveness or causation",
        "ranking, forecasting, prediction",
        "hidden assessment metadata",
    ):
        assert phrase in source
    assert "rangeEnd <= filters.rangeStart" in source
    assert "source_excluded_record_count" in source


def test_education_page_integrates_trend_interface():
    source = (ROOT / "app/education/page.tsx").read_text()
    assert "LearnerRoadmapOutcomeTrends" in source
    assert "<LearnerRoadmapOutcomeTrends />" in source
