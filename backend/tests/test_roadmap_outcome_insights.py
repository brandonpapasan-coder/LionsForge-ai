from datetime import datetime, timezone

from app.services.roadmap_outcome_insights import (
    ADVISORY_NOTICE,
    MIN_GROUP_SIZE,
    build_insights,
    build_receipt,
    validate_insights,
    validate_receipt,
)

NOW = datetime(2026, 7, 27, 16, 0, tzinfo=timezone.utc)


def source_report():
    return {
        "schema": "lionsforge.roadmap-action-outcome-report",
        "schema_version": 1,
        "generator_version": "1.0.0",
        "learner_user_id": 7,
        "generated_at": "2026-07-27T15:00:00Z",
        "entries": [
            {
                "learner_user_id": 7,
                "enrollment_id": 1,
                "outcome_status": "completed",
                "template_slug": "source-validation",
                "template_version": 1,
                "research_project_id": 11,
                "recommendation_reason_codes": ["adds_not_yet_demonstrated_competency"],
                "action_sha256": "a" * 64,
                "action_receipt_sha256": "b" * 64,
                "acted_at": "2026-07-20T12:00:00Z",
                "completed_at": "2026-07-22T12:00:00Z",
                "completion_record_sha256": "c" * 64,
            },
            {
                "learner_user_id": 7,
                "enrollment_id": 2,
                "outcome_status": "completed",
                "template_slug": "source-validation",
                "template_version": 1,
                "research_project_id": 12,
                "recommendation_reason_codes": ["adds_not_yet_demonstrated_competency"],
                "action_sha256": "d" * 64,
                "action_receipt_sha256": "e" * 64,
                "acted_at": "2026-07-21T12:00:00Z",
                "completed_at": "2026-07-24T12:00:00Z",
                "completion_record_sha256": "f" * 64,
            },
            {
                "learner_user_id": 7,
                "enrollment_id": 3,
                "outcome_status": "in_progress",
                "template_slug": "source-validation",
                "template_version": 1,
                "research_project_id": 13,
                "recommendation_reason_codes": ["strengthens_developing_competency"],
                "action_sha256": "1" * 64,
                "action_receipt_sha256": "2" * 64,
                "acted_at": "2026-07-25T12:00:00Z",
                "completed_at": None,
                "completion_record_sha256": None,
            },
        ],
        "excluded_record_count": 1,
        "excluded_findings": ["one stored action failed integrity requirements"],
        "advisory_notice": "source notice",
    }


def test_builds_deterministic_summary_and_receipt():
    insights = build_insights(source_report=source_report(), generated_at=NOW)
    assert insights["learner_user_id"] == 7
    assert insights["total_action_count"] == 3
    assert insights["status_counts"] == {
        "not_started": 0,
        "in_progress": 1,
        "review_ready": 0,
        "completed": 2,
    }
    assert insights["completed_rate"] == 0.6667
    assert insights["median_completion_hours"] == 60.0
    assert insights["source_excluded_record_count"] == 1
    assert insights["advisory_notice"] == ADVISORY_NOTICE
    receipt = build_receipt(insights, generated_at=NOW)
    assert validate_receipt(receipt, insights) == []


def test_group_statistics_require_minimum_size():
    insights = build_insights(source_report=source_report(), generated_at=NOW)
    template = insights["by_template"][0]
    assert template["action_count"] == MIN_GROUP_SIZE
    assert template["statistics_suppressed"] is False
    reasons = {row["group_key"]: row for row in insights["by_recommendation_reason"]}
    assert reasons["adds_not_yet_demonstrated_competency"]["statistics_suppressed"] is True
    assert reasons["adds_not_yet_demonstrated_competency"]["completed_rate"] is None
    assert reasons["strengthens_developing_competency"]["median_completion_hours"] is None


def test_empty_report_is_valid_without_fabricated_rates():
    report = source_report()
    report["entries"] = []
    insights = build_insights(source_report=report, generated_at=NOW)
    assert insights["total_action_count"] == 0
    assert insights["completed_rate"] is None
    assert insights["median_completion_hours"] is None
    assert insights["by_template"] == []
    assert validate_insights(insights) == []


def test_rejects_private_fields_and_suppression_drift():
    insights = build_insights(source_report=source_report(), generated_at=NOW)
    insights["project_title"] = "private"
    assert any("prohibited private-content" in finding for finding in validate_insights(insights))

    insights = build_insights(source_report=source_report(), generated_at=NOW)
    insights["by_recommendation_reason"][0]["statistics_suppressed"] = False
    assert any("suppression mismatch" in finding for finding in validate_insights(insights))


def test_receipt_detects_report_and_count_substitution():
    insights = build_insights(source_report=source_report(), generated_at=NOW)
    receipt = build_receipt(insights, generated_at=NOW)
    receipt["total_action_count"] = 99
    assert "total action count mismatch" in validate_receipt(receipt, insights)

    receipt = build_receipt(insights, generated_at=NOW)
    receipt["source_report_sha256"] = "0" * 64
    assert "source report digest mismatch" in validate_receipt(receipt, insights)
