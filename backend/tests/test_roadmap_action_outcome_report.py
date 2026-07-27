from copy import deepcopy
from datetime import datetime, timezone

import pytest

from app.services.roadmap_action_outcome_report import (
    ADVISORY_NOTICE,
    build_receipt,
    build_report,
    canonical_json,
    validate_entry,
    validate_receipt,
    validate_report,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def entry(*, enrollment_id: int = 10, status: str = "in_progress") -> dict:
    return {
        "learner_user_id": 7,
        "enrollment_id": enrollment_id,
        "outcome_status": status,
        "template_slug": "source-validation-foundations",
        "template_version": 1,
        "research_project_id": 22,
        "recommendation_reason_codes": ["strengthens_developing_competency"],
        "action_sha256": DIGEST_A,
        "action_receipt_sha256": DIGEST_B,
        "acted_at": "2026-07-27T12:00:00Z",
        "completed_at": "2026-07-27T13:00:00Z" if status == "completed" else None,
        "completion_record_sha256": DIGEST_C if status == "completed" else None,
    }


def bundle() -> tuple[dict, dict]:
    generated = datetime(2026, 7, 27, 14, 0, tzinfo=timezone.utc)
    report = build_report(learner_user_id=7, generated_at=generated, entries=[entry(status="completed")])
    return report, build_receipt(report, generated_at=generated)


def test_builds_canonical_deterministic_report_and_receipt() -> None:
    generated = datetime(2026, 7, 27, 14, 0, tzinfo=timezone.utc)
    earlier = entry(enrollment_id=9)
    earlier["acted_at"] = "2026-07-26T12:00:00Z"
    report = build_report(
        learner_user_id=7,
        generated_at=generated,
        entries=[earlier, entry(enrollment_id=10, status="completed")],
    )
    receipt = build_receipt(report, generated_at=generated)

    assert [item["enrollment_id"] for item in report["entries"]] == [10, 9]
    assert report["advisory_notice"] == ADVISORY_NOTICE
    assert receipt["entry_count"] == 2
    assert receipt["completed_entry_count"] == 1
    assert canonical_json(report).endswith("\n")
    assert validate_report(report) == []
    assert validate_receipt(receipt, report) == []


def test_requires_completion_provenance_only_for_completed_outcomes() -> None:
    missing = entry(status="completed")
    missing["completed_at"] = None
    missing["completion_record_sha256"] = None
    assert "completed outcome requires completed_at" in validate_entry(missing, learner_user_id=7)
    assert "completed outcome requires completion_record_sha256" in validate_entry(missing, learner_user_id=7)

    leaked = entry(status="in_progress")
    leaked["completed_at"] = "2026-07-27T13:00:00Z"
    leaked["completion_record_sha256"] = DIGEST_C
    assert "non-completed outcome must not include completion provenance" in validate_entry(leaked, learner_user_id=7)


def test_rejects_learner_drift_duplicate_enrollments_and_private_fields() -> None:
    generated = datetime(2026, 7, 27, 14, 0, tzinfo=timezone.utc)
    first = entry()
    second = deepcopy(first)
    second["project_title"] = "private"
    report = {
        "schema": "lionsforge.roadmap-action-outcome-report",
        "schema_version": 1,
        "generator_version": "1.0.0",
        "learner_user_id": 8,
        "generated_at": "2026-07-27T14:00:00Z",
        "entries": [first, second],
        "excluded_record_count": 0,
        "excluded_findings": [],
        "advisory_notice": ADVISORY_NOTICE,
    }
    findings = validate_report(report)
    assert "duplicate enrollment_id in report" in findings
    assert "outcome entry learner binding mismatch" in findings
    assert any("prohibited private-content field" in finding for finding in findings)


def test_receipt_detects_report_and_count_substitution() -> None:
    report, receipt = bundle()
    drifted = deepcopy(report)
    drifted["entries"][0]["template_version"] = 2
    findings = validate_receipt(receipt, drifted)
    assert "report digest mismatch" in findings

    count_drift = deepcopy(receipt)
    count_drift["completed_entry_count"] = 0
    assert "completed entry count mismatch" in validate_receipt(count_drift, report)


def test_build_report_fails_closed_for_invalid_rows() -> None:
    invalid = entry()
    invalid["action_sha256"] = "not-a-digest"
    with pytest.raises(ValueError, match="Invalid roadmap action outcome report"):
        build_report(
            learner_user_id=7,
            generated_at=datetime.now(timezone.utc),
            entries=[invalid],
        )
