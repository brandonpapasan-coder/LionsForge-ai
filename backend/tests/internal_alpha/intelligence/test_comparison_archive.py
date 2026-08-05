import copy

import pytest

from app.internal_alpha.intelligence.bundle import build_intelligence_bundle
from app.internal_alpha.intelligence.comparison import compare_intelligence_bundles
from app.internal_alpha.intelligence.comparison_archive import (
    build_intelligence_comparison_archive,
    validate_intelligence_comparison_archive,
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
    receipt = build_intelligence_comparison_receipt(
        comparison,
        baseline,
        candidate,
    )
    return build_intelligence_comparison_archive(
        baseline,
        candidate,
        comparison,
        receipt,
    )


def test_builds_deterministic_archive() -> None:
    first = _archive()
    second = _archive()

    assert first == second
    assert len(first["archive_sha256"]) == 64
    assert validate_intelligence_comparison_archive(first) == []


def test_rejects_non_object_and_extra_keys() -> None:
    assert validate_intelligence_comparison_archive([]) == [  # type: ignore[arg-type]
        "comparison archive must be an object"
    ]

    archive = _archive()
    archive["extra"] = "field"
    assert "comparison archive keys invalid" in validate_intelligence_comparison_archive(
        archive
    )


def test_rejects_coercive_schema_version() -> None:
    archive = _archive()
    archive["schema_version"] = True

    assert validate_intelligence_comparison_archive(archive) == [
        "comparison archive schema version mismatch"
    ]


def test_rejects_noncanonical_and_substituted_digests() -> None:
    archive = _archive()

    uppercase = copy.deepcopy(archive)
    uppercase["archive_sha256"] = "A" * 64
    findings = validate_intelligence_comparison_archive(uppercase)
    assert "comparison archive digest invalid" in findings
    assert "comparison archive digest mismatch" in findings

    malformed = copy.deepcopy(archive)
    malformed["archive_sha256"] = 7
    findings = validate_intelligence_comparison_archive(malformed)
    assert "comparison archive digest invalid" in findings
    assert "comparison archive digest mismatch" in findings

    substituted = copy.deepcopy(archive)
    substituted["archive_sha256"] = "0" * 64
    assert validate_intelligence_comparison_archive(substituted) == [
        "comparison archive digest mismatch"
    ]


def test_rejects_payload_object_and_receipt_chain_drift() -> None:
    archive = _archive()

    malformed = copy.deepcopy(archive)
    malformed["comparison"] = []
    findings = validate_intelligence_comparison_archive(malformed)
    assert "comparison archive payload objects invalid" in findings

    drifted = copy.deepcopy(archive)
    drifted_receipt = drifted["receipt"]
    assert isinstance(drifted_receipt, dict)
    drifted_receipt["verification_state"] = "INVALID"
    findings = validate_intelligence_comparison_archive(drifted)
    assert "comparison receipt verification_state mismatch" in findings
    assert "comparison archive digest mismatch" in findings


def test_refuses_to_build_from_invalid_receipt_chain() -> None:
    archive = _archive()
    receipt = copy.deepcopy(archive["receipt"])
    assert isinstance(receipt, dict)
    receipt["receipt_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="invalid comparison receipt chain"):
        build_intelligence_comparison_archive(
            archive["baseline"],  # type: ignore[arg-type]
            archive["candidate"],  # type: ignore[arg-type]
            archive["comparison"],  # type: ignore[arg-type]
            receipt,
        )
