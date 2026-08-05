import copy

import pytest

from app.internal_alpha.intelligence.bundle import build_intelligence_bundle
from app.internal_alpha.intelligence.comparison import compare_intelligence_bundles
from app.internal_alpha.intelligence.comparison_archive import (
    build_intelligence_comparison_archive,
)
from app.internal_alpha.intelligence.comparison_archive_receipt import (
    build_intelligence_comparison_archive_receipt,
    validate_intelligence_comparison_archive_receipt,
)
from app.internal_alpha.intelligence.comparison_receipt import (
    build_intelligence_comparison_receipt,
)
from app.internal_alpha.intelligence.receipt import build_intelligence_receipt


def _entry(candidate_sha: str, feedback_items: int) -> dict[str, object]:
    report: dict[str, object] = {
        "schema": "lionsforge.internal-alpha-intelligence-report",
        "schema_version": 1,
        "candidate_sha": candidate_sha,
        "metrics": {
            "active_testers": 5,
            "active_experiments": 2,
            "feedback_items": feedback_items,
            "completed_experiments": 1,
        },
        "readiness": {
            "security": 95.0,
            "reliability": 94.0,
            "feedback": 92.0,
            "regression": 96.0,
            "overall": 94.25,
            "state": "READY",
        },
        "repeated_categories": [],
        "blocking_reasons": [],
        "interpretation_notice": (
            "This report summarizes bounded internal-alpha evidence and does not authorize "
            "public beta, production deployment, or general availability."
        ),
    }
    return {"report": report, "receipt": build_intelligence_receipt(report)}


def _archive() -> dict[str, object]:
    baseline = build_intelligence_bundle(
        [_entry("a" * 40, 8), _entry("b" * 40, 8)]
    )
    candidate = build_intelligence_bundle(
        [_entry("a" * 40, 9), _entry("c" * 40, 8)]
    )
    comparison = compare_intelligence_bundles(baseline, candidate)
    comparison_receipt = build_intelligence_comparison_receipt(
        comparison,
        baseline,
        candidate,
    )
    return build_intelligence_comparison_archive(
        baseline,
        candidate,
        comparison,
        comparison_receipt,
    )


def test_issues_deterministic_archive_receipt() -> None:
    archive = _archive()
    first = build_intelligence_comparison_archive_receipt(archive)
    second = build_intelligence_comparison_archive_receipt(archive)

    assert first == second
    assert first["archive_sha256"] == archive["archive_sha256"]
    assert first["verification_state"] == "VERIFIED"
    assert len(first["receipt_sha256"]) == 64
    assert validate_intelligence_comparison_archive_receipt(first, archive) == []


def test_rejects_non_object_extra_keys_and_coercive_schema_version() -> None:
    archive = _archive()

    malformed_findings = validate_intelligence_comparison_archive_receipt(
        [],  # type: ignore[arg-type]
        archive,
    )
    assert malformed_findings == ["comparison archive receipt must be an object"]

    receipt = build_intelligence_comparison_archive_receipt(archive)
    receipt["extra"] = "field"
    assert "comparison archive receipt keys invalid" in (
        validate_intelligence_comparison_archive_receipt(receipt, archive)
    )

    coercive = build_intelligence_comparison_archive_receipt(archive)
    coercive["schema_version"] = True
    assert validate_intelligence_comparison_archive_receipt(coercive, archive) == [
        "comparison archive receipt schema version mismatch"
    ]


def test_rejects_receipt_drift_and_digest_substitution() -> None:
    archive = _archive()
    receipt = build_intelligence_comparison_archive_receipt(archive)

    drifted = copy.deepcopy(receipt)
    drifted["verification_state"] = "INVALID"
    assert validate_intelligence_comparison_archive_receipt(drifted, archive) == [
        "comparison archive receipt verification_state mismatch"
    ]

    substituted = copy.deepcopy(receipt)
    substituted["receipt_sha256"] = "0" * 64
    assert validate_intelligence_comparison_archive_receipt(substituted, archive) == [
        "comparison archive receipt digest mismatch"
    ]


def test_rejects_noncanonical_archive_and_receipt_digests() -> None:
    archive = _archive()
    receipt = build_intelligence_comparison_archive_receipt(archive)

    uppercase_archive = copy.deepcopy(receipt)
    uppercase_archive["archive_sha256"] = "A" * 64
    findings = validate_intelligence_comparison_archive_receipt(
        uppercase_archive,
        archive,
    )
    assert "comparison archive receipt archive_sha256 invalid" in findings
    assert "comparison archive receipt archive_sha256 mismatch" in findings

    malformed_archive = copy.deepcopy(receipt)
    malformed_archive["archive_sha256"] = 7
    findings = validate_intelligence_comparison_archive_receipt(
        malformed_archive,
        archive,
    )
    assert "comparison archive receipt archive_sha256 invalid" in findings
    assert "comparison archive receipt archive_sha256 mismatch" in findings

    uppercase_receipt = copy.deepcopy(receipt)
    uppercase_receipt["receipt_sha256"] = "A" * 64
    findings = validate_intelligence_comparison_archive_receipt(
        uppercase_receipt,
        archive,
    )
    assert findings == [
        "comparison archive receipt digest invalid",
        "comparison archive receipt digest mismatch",
    ]

    malformed_receipt = copy.deepcopy(receipt)
    malformed_receipt["receipt_sha256"] = 7
    findings = validate_intelligence_comparison_archive_receipt(
        malformed_receipt,
        archive,
    )
    assert findings == [
        "comparison archive receipt digest invalid",
        "comparison archive receipt digest mismatch",
    ]


def test_rejects_archive_drift() -> None:
    archive = _archive()
    receipt = build_intelligence_comparison_archive_receipt(archive)

    drifted_archive = copy.deepcopy(archive)
    drifted_archive["archive_sha256"] = "0" * 64
    findings = validate_intelligence_comparison_archive_receipt(
        receipt,
        drifted_archive,
    )
    assert "comparison archive digest mismatch" in findings
    assert "comparison archive receipt archive_sha256 mismatch" in findings
    assert "comparison archive receipt digest mismatch" in findings


def test_refuses_to_issue_receipt_for_invalid_archive() -> None:
    archive = _archive()
    archive["archive_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="invalid comparison archive"):
        build_intelligence_comparison_archive_receipt(archive)
