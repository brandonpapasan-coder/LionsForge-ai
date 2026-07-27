from copy import deepcopy
from datetime import datetime, timezone

from app.services.learner_competency_portfolio import (
    ADVISORY_NOTICE,
    build_portfolio,
    build_receipt,
    canonical_json,
    validate_portfolio,
    validate_receipt,
)


def _rows():
    return [
        {
            "competency_key": "evidence-validation",
            "competency_label": "Evidence validation",
            "enrollment_id": 12,
            "template_slug": "research-validation",
            "template_version": 2,
            "research_project_id": 44,
            "completed_at": datetime(2026, 7, 2, 12, tzinfo=timezone.utc),
            "objective_keys": ["source-quality", "claim-traceability"],
            "referenced_evidence_ids": [8, 3, 8],
            "final_review_decision_id": 91,
            "completion_record_sha256": "a" * 64,
        },
        {
            "competency_key": "research-design",
            "competency_label": "Research design",
            "enrollment_id": 11,
            "template_slug": "applied-research",
            "template_version": 1,
            "research_project_id": 41,
            "completed_at": datetime(2026, 7, 1, 12, tzinfo=timezone.utc),
            "objective_keys": ["method-selection"],
            "referenced_evidence_ids": [2],
            "final_review_decision_id": 90,
            "completion_record_sha256": "b" * 64,
        },
    ]


def _portfolio():
    return build_portfolio(
        learner_user_id=7,
        generated_at=datetime(2026, 7, 3, 12, tzinfo=timezone.utc),
        competency_rows=list(reversed(_rows())),
        excluded_record_count=1,
    )


def test_build_portfolio_is_canonical_and_deterministic():
    portfolio = _portfolio()
    again = build_portfolio(
        learner_user_id=7,
        generated_at=datetime(2026, 7, 3, 12, tzinfo=timezone.utc),
        competency_rows=_rows(),
        excluded_record_count=1,
    )

    assert canonical_json(portfolio) == canonical_json(again)
    assert [item["competency_key"] for item in portfolio["competencies"]] == [
        "evidence-validation",
        "research-design",
    ]
    assert portfolio["competencies"][0]["practica"][0]["referenced_evidence_ids"] == [3, 8]
    assert portfolio["advisory_notice"] == ADVISORY_NOTICE
    assert validate_portfolio(portfolio) == []


def test_receipt_detects_portfolio_drift():
    portfolio = _portfolio()
    receipt = build_receipt(portfolio, generated_at=datetime(2026, 7, 3, 12, 1, tzinfo=timezone.utc))
    assert validate_receipt(receipt, portfolio) == []

    changed = deepcopy(portfolio)
    changed["excluded_record_count"] = 2
    assert "portfolio digest mismatch" in validate_receipt(receipt, changed)


def test_validation_rejects_duplicates_and_private_fields_deterministically():
    portfolio = _portfolio()
    duplicate = deepcopy(portfolio["competencies"][0])
    portfolio["competencies"].append(duplicate)
    portfolio["reviewer_notes"] = "must never be exported"

    findings = validate_portfolio(portfolio)
    assert findings == sorted(set(findings))
    assert "duplicate competency_key" in findings
    assert "unexpected portfolio field: reviewer_notes" in findings
    assert "prohibited private-content field at $.reviewer_notes" in findings


def test_validation_rejects_bad_order_counts_and_digest():
    portfolio = _portfolio()
    portfolio["competencies"] = list(reversed(portfolio["competencies"]))
    portfolio["competencies"][0]["completed_practicum_count"] = 99
    portfolio["competencies"][0]["practica"][0]["completion_record_sha256"] = "bad"

    findings = validate_portfolio(portfolio)
    assert "competencies must use deterministic key ordering" in findings
    assert "completed_practicum_count mismatch" in findings
    assert "completion_record_sha256 must be a lowercase SHA-256 digest" in findings


def test_empty_portfolio_is_valid_for_learner_without_completed_practica():
    portfolio = build_portfolio(
        learner_user_id=9,
        generated_at=datetime(2026, 7, 3, 12, tzinfo=timezone.utc),
        competency_rows=[],
    )
    assert portfolio["competencies"] == []
    assert validate_portfolio(portfolio) == []
