from copy import deepcopy
from datetime import datetime, timezone

import pytest

from app.services.roadmap_action_ledger import (
    ADVISORY_NOTICE,
    build_ledger,
    build_receipt,
    canonical_json,
    validate_ledger,
    validate_receipt,
)

NOW = datetime(2026, 7, 27, 12, 50, tzinfo=timezone.utc)


def entry(*, enrollment_id: int, acted_at: str) -> dict:
    return {
        "learner_user_id": 7,
        "enrollment_id": enrollment_id,
        "enrollment_status": "in_progress",
        "template_slug": f"evidence-practicum-{enrollment_id}",
        "template_version": 1,
        "research_project_id": 40 + enrollment_id,
        "recommendation_reason_codes": [
            "strengthens_developing_competency",
            "adds_not_yet_demonstrated_competency",
            "strengthens_developing_competency",
        ],
        "roadmap_plan_sha256": "a" * 64,
        "portfolio_sha256": "b" * 64,
        "action_sha256": "c" * 64,
        "action_receipt_sha256": "d" * 64,
        "acted_at": acted_at,
    }


def test_builds_canonical_reverse_chronological_ledger_and_receipt() -> None:
    ledger = build_ledger(
        learner_user_id=7,
        generated_at=NOW,
        entries=[
            entry(enrollment_id=1, acted_at="2026-07-27T11:00:00Z"),
            entry(enrollment_id=2, acted_at="2026-07-27T12:00:00Z"),
        ],
        excluded_record_count=1,
        excluded_findings=["row 9 failed integrity", "row 9 failed integrity"],
    )
    receipt = build_receipt(ledger, generated_at=NOW)

    assert [item["enrollment_id"] for item in ledger["entries"]] == [2, 1]
    assert ledger["entries"][0]["recommendation_reason_codes"] == [
        "adds_not_yet_demonstrated_competency",
        "strengthens_developing_competency",
    ]
    assert ledger["excluded_findings"] == ["row 9 failed integrity"]
    assert ledger["advisory_notice"] == ADVISORY_NOTICE
    assert receipt["entry_count"] == 2
    assert receipt["excluded_record_count"] == 1
    assert validate_receipt(receipt, ledger) == []
    assert canonical_json(ledger).endswith("\n")


def test_rejects_duplicate_enrollment_and_learner_binding_drift() -> None:
    first = entry(enrollment_id=1, acted_at="2026-07-27T12:00:00Z")
    second = deepcopy(first)
    second["learner_user_id"] = 8
    ledger = {
        "schema": "lionsforge.roadmap-action-ledger",
        "schema_version": 1,
        "generator_version": "1.0.0",
        "learner_user_id": 7,
        "generated_at": "2026-07-27T12:50:00Z",
        "entries": [first, second],
        "excluded_record_count": 0,
        "excluded_findings": [],
        "advisory_notice": ADVISORY_NOTICE,
    }

    findings = validate_ledger(ledger)
    assert "duplicate enrollment_id in ledger" in findings
    assert "ledger entry learner binding mismatch" in findings


def test_detects_ledger_drift_and_receipt_count_substitution() -> None:
    ledger = build_ledger(
        learner_user_id=7,
        generated_at=NOW,
        entries=[entry(enrollment_id=1, acted_at="2026-07-27T12:00:00Z")],
    )
    receipt = build_receipt(ledger, generated_at=NOW)
    drifted = deepcopy(ledger)
    drifted["entries"][0]["enrollment_status"] = "completed"
    receipt["entry_count"] = 2

    findings = validate_receipt(receipt, drifted)
    assert "ledger digest mismatch" in findings
    assert "ledger entry count mismatch" in findings


def test_rejects_private_fields_malformed_digest_and_timestamp() -> None:
    row = entry(enrollment_id=1, acted_at="not-a-time")
    row["project_title"] = "Secret project"
    row["action_sha256"] = "BAD"
    ledger = {
        "schema": "lionsforge.roadmap-action-ledger",
        "schema_version": 1,
        "generator_version": "1.0.0",
        "learner_user_id": 7,
        "generated_at": "2026-07-27T12:50:00Z",
        "entries": [row],
        "excluded_record_count": 0,
        "excluded_findings": [],
        "advisory_notice": ADVISORY_NOTICE,
    }

    findings = validate_ledger(ledger)
    assert "acted_at must be a UTC Z timestamp" in findings
    assert "action_sha256 must be a lowercase SHA-256 digest" in findings
    assert any("prohibited private-content field" in item for item in findings)


def test_build_fails_closed_for_invalid_entry() -> None:
    bad = entry(enrollment_id=1, acted_at="2026-07-27T12:00:00Z")
    bad["recommendation_reason_codes"] = []

    with pytest.raises(ValueError, match="Invalid roadmap action ledger"):
        build_ledger(learner_user_id=7, generated_at=NOW, entries=[bad])
