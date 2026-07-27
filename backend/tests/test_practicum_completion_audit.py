from copy import deepcopy
from datetime import datetime, timezone

import pytest

from app.services.practicum_completion_audit import (
    ADVISORY_NOTICE,
    build_receipt,
    build_record,
    canonical_json,
    sha256_digest,
    validate_receipt,
    validate_record,
)

COMPLETED_AT = datetime(2026, 7, 27, 2, 0, tzinfo=timezone.utc)
GENERATED_AT = datetime(2026, 7, 27, 2, 5, tzinfo=timezone.utc)


def _record():
    return build_record(
        enrollment_id=41,
        learner_user_id=7,
        template_slug="evidence-validation-practicum",
        template_version=2,
        research_project_id=83,
        completed_at=COMPLETED_AT,
        objectives=[
            {
                "objective_key": "defend-conclusion",
                "sequence": 2,
                "status": "approved",
                "referenced_evidence_ids": [9, 7, 9],
            },
            {
                "objective_key": "validate-evidence",
                "sequence": 1,
                "status": "approved",
                "referenced_evidence_ids": [4, 3],
            },
        ],
        review_history=[
            {
                "decision_id": 11,
                "reviewer_user_id": 91,
                "decision": "revision_required",
                "created_at": datetime(2026, 7, 26, 20, 0, tzinfo=timezone.utc),
            },
            {
                "decision_id": 12,
                "reviewer_user_id": 92,
                "decision": "approved",
                "created_at": datetime(2026, 7, 27, 1, 59, tzinfo=timezone.utc),
            },
        ],
    )


def test_build_record_is_canonical_private_content_free_and_deterministic():
    record = _record()

    assert record["status"] == "completed"
    assert record["advisory_notice"] == ADVISORY_NOTICE
    assert [item["objective_key"] for item in record["objectives"]] == [
        "validate-evidence",
        "defend-conclusion",
    ]
    assert record["objectives"][1]["referenced_evidence_ids"] == [7, 9]
    assert record["review_history"][-1]["decision"] == "approved"
    assert all(item["decision_source"] == "human_reviewer" for item in record["review_history"])
    assert "reflection" not in canonical_json(record)
    assert validate_record(record) == []
    assert canonical_json(record) == canonical_json(_record())


def test_receipt_binds_exact_canonical_record_digest():
    record = _record()
    receipt = build_receipt(record, generated_at=GENERATED_AT)

    assert receipt["record_sha256"] == sha256_digest(record)
    assert receipt["generated_at"] == "2026-07-27T02:05:00Z"
    assert validate_receipt(receipt, record) == []


def test_receipt_detects_record_drift():
    record = _record()
    receipt = build_receipt(record, generated_at=GENERATED_AT)
    drifted = deepcopy(record)
    drifted["research_project_id"] = 84

    assert "record digest mismatch" in validate_receipt(receipt, drifted)


def test_record_rejects_incomplete_or_nonhuman_completion():
    record = _record()
    record["status"] = "revision_required"
    record["review_history"][-1]["decision_source"] = "deterministic_rules"

    findings = validate_record(record)

    assert "record status must be completed" in findings
    assert "review decision source must be human_reviewer" in findings


def test_record_rejects_unsorted_duplicate_and_private_fields():
    record = _record()
    record["objectives"] = list(reversed(record["objectives"]))
    record["objectives"][0]["referenced_evidence_ids"] = [9, 9, 7]
    record["review_history"].append(deepcopy(record["review_history"][-1]))
    record["reflection"] = "private learner-authored text"

    findings = validate_record(record)

    assert "objectives must use deterministic sequence ordering" in findings
    assert "evidence IDs must be unique and sorted" in findings
    assert "duplicate decision_id" in findings
    assert "unexpected record field: reflection" in findings
    assert "prohibited private-content field at $.reflection" in findings


def test_build_record_refuses_nonapproved_objective():
    with pytest.raises(ValueError, match="completed record objectives must be approved"):
        build_record(
            enrollment_id=41,
            learner_user_id=7,
            template_slug="evidence-validation-practicum",
            template_version=2,
            research_project_id=83,
            completed_at=COMPLETED_AT,
            objectives=[
                {
                    "objective_key": "validate-evidence",
                    "sequence": 1,
                    "status": "ready_for_review",
                    "referenced_evidence_ids": [3],
                }
            ],
            review_history=[
                {
                    "decision_id": 12,
                    "reviewer_user_id": 92,
                    "decision": "approved",
                    "created_at": COMPLETED_AT,
                }
            ],
        )


def test_findings_are_deterministically_sorted():
    record = _record()
    record["status"] = "in_progress"
    record["completed_at"] = "not-a-time"
    record["extra"] = True

    findings = validate_record(record)

    assert findings == sorted(findings)
