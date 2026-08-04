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


def test_build_rejects_extra_report_fields() -> None:
    with pytest.raises(ValueError, match="invalid intelligence report shape"):
        build_intelligence_receipt({**_report(), "unexpected": True})


@pytest.mark.parametrize(
    "changes",
    [
        {"candidate_sha": "A" * 40},
        {"candidate_sha": True},
        {"metrics": []},
        {"readiness": []},
        {"repeated_categories": {}},
        {"blocking_reasons": {}},
        {"interpretation_notice": 1},
    ],
)
def test_build_rejects_noncanonical_report_types(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="invalid intelligence report shape"):
        build_intelligence_receipt({**_report(), **changes})


def test_validation_rejects_extra_receipt_fields() -> None:
    report = _report()
    receipt = {**build_intelligence_receipt(report), "unexpected": True}
    assert validate_intelligence_receipt(receipt, report) == [
        "invalid intelligence receipt"
    ]


@pytest.mark.parametrize(
    "changes",
    [
        {"candidate_sha": "A" * 40},
        {"candidate_sha": True},
        {"report_sha256": "A" * 64},
        {"report_sha256": True},
    ],
)
def test_validation_rejects_noncanonical_receipt_types(
    changes: dict[str, object],
) -> None:
    report = _report()
    receipt = {**build_intelligence_receipt(report), **changes}
    findings = validate_intelligence_receipt(receipt, report)
    assert "invalid intelligence receipt" in findings


def test_validation_rejects_extra_report_fields_fail_closed() -> None:
    report = {**_report(), "unexpected": True}
    receipt = build_intelligence_receipt(_report())
    assert validate_intelligence_receipt(receipt, report) == [
        "invalid intelligence report"
    ]
