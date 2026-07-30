import pytest

from app.internal_alpha.intelligence.receipt import (
    build_intelligence_receipt,
    validate_intelligence_receipt,
)


CANDIDATE = "a" * 40


def _report() -> dict[str, object]:
    return {
        "schema": "lionsforge.internal-alpha-intelligence-report",
        "schema_version": 1,
        "candidate_sha": CANDIDATE,
        "metrics": {"active_testers": 1},
        "readiness": {"state": "NOT_READY"},
        "repeated_categories": [],
        "blocking_reasons": ["READINESS_GUARDRAIL_NOT_MET"],
        "interpretation_notice": "bounded",
    }


def test_builds_deterministic_receipt() -> None:
    first = build_intelligence_receipt(_report())
    second = build_intelligence_receipt(dict(reversed(list(_report().items()))))
    assert first == second
    assert first["candidate_sha"] == CANDIDATE
    assert len(first["report_sha256"]) == 64


def test_validation_detects_candidate_and_digest_substitution() -> None:
    report = _report()
    receipt = build_intelligence_receipt(report)
    substituted = {**receipt, "candidate_sha": "b" * 40, "report_sha256": "0" * 64}
    assert validate_intelligence_receipt(substituted, report) == [
        "candidate SHA mismatch",
        "report digest mismatch",
    ]


def test_rejects_unsupported_report_schema() -> None:
    with pytest.raises(ValueError, match="unsupported intelligence report schema"):
        build_intelligence_receipt({**_report(), "schema_version": 2})
