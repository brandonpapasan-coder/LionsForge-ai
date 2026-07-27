from datetime import datetime, timezone

import pytest

from app.services.roadmap_outcome_trends import (
    build_receipt,
    build_trends,
    validate_receipt,
    validate_trends,
)

NOW = datetime(2026, 7, 27, 18, 0, tzinfo=timezone.utc)


def _entry(index: int, status: str, acted_at: str, completed_at: str | None = None):
    return {
        "learner_user_id": 7,
        "enrollment_id": index,
        "outcome_status": status,
        "template_slug": "source-validation",
        "template_version": "1.0.0",
        "research_project_id": index,
        "recommendation_reason_codes": ["adds_not_yet_demonstrated_competency"],
        "action_sha256": "a" * 64,
        "action_receipt_sha256": "b" * 64,
        "acted_at": acted_at,
        "completed_at": completed_at,
        "completion_record_sha256": "c" * 64 if completed_at else None,
    }


def _report(entries):
    return {
        "schema": "lionsforge.roadmap-action-outcome-report",
        "schema_version": 1,
        "generator_version": "1.0.0",
        "learner_user_id": 7,
        "generated_at": "2026-07-27T18:00:00Z",
        "entries": entries,
        "excluded_record_count": 0,
        "excluded_findings": [],
        "advisory_notice": "source notice",
    }


def test_builds_deterministic_daily_windows_and_receipt():
    report = _report([
        _entry(1, "completed", "2026-07-01T08:00:00Z", "2026-07-01T10:00:00Z"),
        _entry(2, "completed", "2026-07-01T09:00:00Z", "2026-07-01T12:00:00Z"),
        _entry(3, "in_progress", "2026-07-01T11:00:00Z"),
        _entry(4, "review_ready", "2026-07-02T09:00:00Z"),
    ])
    trends = build_trends(
        source_report=report,
        granularity="day",
        range_start=datetime(2026, 7, 1, 5, tzinfo=timezone.utc),
        range_end=datetime(2026, 7, 3, tzinfo=timezone.utc),
        generated_at=NOW,
    )
    assert trends["range_start"] == "2026-07-01T00:00:00Z"
    assert len(trends["windows"]) == 2
    assert trends["windows"][0]["completed_rate"] == 0.6667
    assert trends["windows"][0]["median_completion_hours"] == 2.5
    assert trends["windows"][1]["statistics_suppressed"] is True
    receipt = build_receipt(trends, generated_at=NOW)
    assert validate_receipt(receipt, trends) == []


def test_supports_week_and_month_boundaries():
    report = _report([])
    weekly = build_trends(
        source_report=report,
        granularity="week",
        range_start=datetime(2026, 7, 8, tzinfo=timezone.utc),
        range_end=datetime(2026, 7, 20, tzinfo=timezone.utc),
        generated_at=NOW,
    )
    monthly = build_trends(
        source_report=report,
        granularity="month",
        range_start=datetime(2026, 7, 15, tzinfo=timezone.utc),
        range_end=datetime(2026, 9, 1, tzinfo=timezone.utc),
        generated_at=NOW,
    )
    assert weekly["range_start"] == "2026-07-06T00:00:00Z"
    assert weekly["windows"][0]["window_end"] == "2026-07-13T00:00:00Z"
    assert monthly["range_start"] == "2026-07-01T00:00:00Z"
    assert [row["window_start"] for row in monthly["windows"]] == [
        "2026-07-01T00:00:00Z",
        "2026-08-01T00:00:00Z",
    ]


def test_rejects_negative_duration_and_invalid_ranges():
    report = _report([
        _entry(1, "completed", "2026-07-01T10:00:00Z", "2026-07-01T09:00:00Z"),
        _entry(2, "completed", "2026-07-01T10:00:00Z", "2026-07-01T11:00:00Z"),
        _entry(3, "completed", "2026-07-01T10:00:00Z", "2026-07-01T12:00:00Z"),
    ])
    with pytest.raises(ValueError, match="completed_at cannot precede acted_at"):
        build_trends(
            source_report=report,
            granularity="day",
            range_start=datetime(2026, 7, 1, tzinfo=timezone.utc),
            range_end=datetime(2026, 7, 2, tzinfo=timezone.utc),
            generated_at=NOW,
        )
    with pytest.raises(ValueError, match="range_end must be after range_start"):
        build_trends(
            source_report=_report([]),
            granularity="day",
            range_start=NOW,
            range_end=NOW,
            generated_at=NOW,
        )


def test_validation_rejects_suppression_drift_private_fields_and_receipt_substitution():
    trends = build_trends(
        source_report=_report([]),
        granularity="day",
        range_start=datetime(2026, 7, 1, tzinfo=timezone.utc),
        range_end=datetime(2026, 7, 2, tzinfo=timezone.utc),
        generated_at=NOW,
    )
    trends["windows"][0]["completed_rate"] = 0.0
    trends["project_title"] = "private"
    findings = validate_trends(trends)
    assert "suppressed window statistics must be null" in findings
    assert any("prohibited private-content field" in finding for finding in findings)

    valid = build_trends(
        source_report=_report([]),
        granularity="day",
        range_start=datetime(2026, 7, 1, tzinfo=timezone.utc),
        range_end=datetime(2026, 7, 2, tzinfo=timezone.utc),
        generated_at=NOW,
    )
    receipt = build_receipt(valid, generated_at=NOW)
    receipt["window_count"] = 99
    assert "window count mismatch" in validate_receipt(receipt, valid)
