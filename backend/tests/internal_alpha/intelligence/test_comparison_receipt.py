import copy

import pytest

from app.internal_alpha.intelligence.bundle import build_intelligence_bundle
from app.internal_alpha.intelligence.comparison import compare_intelligence_bundles
from app.internal_alpha.intelligence.comparison_receipt import (
    build_intelligence_comparison_receipt,
    validate_intelligence_comparison_receipt,
)
from app.internal_alpha.intelligence.receipt import build_intelligence_receipt


def _entry(candidate_sha: str, active_testers: int = 1) -> dict[str, object]:
    report: dict[str, object] = {
        "schema": "lionsforge.internal-alpha-intelligence-report",
        "schema_version": 1,
        "candidate_sha": candidate_sha,
        "metrics": {"active_testers": active_testers},
        "readiness": {"state": "READY"},
        "repeated_categories": [],
        "blocking_reasons": [],
        "interpretation_notice": "bounded",
    }
    return {"report": report, "receipt": build_intelligence_receipt(report)}


def _artifacts() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    baseline = build_intelligence_bundle([_entry("a" * 40), _entry("b" * 40)])
    candidate = build_intelligence_bundle(
        [_entry("b" * 40, active_testers=2), _entry("c" * 40)]
    )
    comparison = compare_intelligence_bundles(baseline, candidate)
    return comparison, baseline, candidate


def test_issues_deterministic_strict_receipt() -> None:
    comparison, baseline, candidate = _artifacts()

    first = build_intelligence_comparison_receipt(comparison, baseline, candidate)
    second = build_intelligence_comparison_receipt(comparison, baseline, candidate)

    assert first == second
    assert first["verification_state"] == "VERIFIED"
    assert len(first["receipt_sha256"]) == 64
    assert validate_intelligence_comparison_receipt(
        first, comparison, baseline, candidate
    ) == []


def test_rejects_non_object_and_extra_fields() -> None:
    comparison, baseline, candidate = _artifacts()
    receipt = build_intelligence_comparison_receipt(comparison, baseline, candidate)

    assert validate_intelligence_comparison_receipt(
        [],  # type: ignore[arg-type]
        comparison,
        baseline,
        candidate,
    ) == ["comparison receipt must be an object"]

    extra = {**receipt, "extra": "field"}
    findings = validate_intelligence_comparison_receipt(
        extra, comparison, baseline, candidate
    )
    assert "comparison receipt keys invalid" in findings


def test_rejects_coercive_versions_and_noncanonical_digests() -> None:
    comparison, baseline, candidate = _artifacts()
    receipt = build_intelligence_comparison_receipt(comparison, baseline, candidate)

    coercive_version = {**receipt, "schema_version": True}
    findings = validate_intelligence_comparison_receipt(
        coercive_version, comparison, baseline, candidate
    )
    assert "comparison receipt schema version invalid" in findings

    uppercase_digest = {**receipt, "receipt_sha256": "A" * 64}
    findings = validate_intelligence_comparison_receipt(
        uppercase_digest, comparison, baseline, candidate
    )
    assert "comparison receipt digest invalid" in findings
    assert "comparison receipt digest mismatch" in findings

    malformed_binding = {**receipt, "comparison_sha256": 7}
    findings = validate_intelligence_comparison_receipt(
        malformed_binding, comparison, baseline, candidate
    )
    assert "comparison receipt comparison_sha256 invalid" in findings
    assert "comparison receipt comparison_sha256 mismatch" in findings


def test_preserves_binding_and_payload_drift_findings() -> None:
    comparison, baseline, candidate = _artifacts()
    receipt = build_intelligence_comparison_receipt(comparison, baseline, candidate)

    substituted = copy.deepcopy(receipt)
    substituted["baseline_bundle_sha256"] = "0" * 64
    findings = validate_intelligence_comparison_receipt(
        substituted, comparison, baseline, candidate
    )
    assert "comparison receipt baseline_bundle_sha256 mismatch" in findings

    drifted_comparison = copy.deepcopy(comparison)
    drifted_comparison["comparison_sha256"] = "0" * 64
    findings = validate_intelligence_comparison_receipt(
        receipt, drifted_comparison, baseline, candidate
    )
    assert "comparison digest mismatch" in findings
    assert "comparison receipt comparison_sha256 mismatch" in findings
    assert "comparison receipt digest mismatch" in findings


def test_refuses_to_issue_receipt_for_invalid_comparison() -> None:
    comparison, baseline, candidate = _artifacts()
    comparison["comparison_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="invalid comparison"):
        build_intelligence_comparison_receipt(comparison, baseline, candidate)
