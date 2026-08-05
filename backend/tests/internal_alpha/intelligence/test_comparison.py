import copy

import pytest

from app.internal_alpha.intelligence.bundle import build_intelligence_bundle
from app.internal_alpha.intelligence.comparison import (
    compare_intelligence_bundles,
    validate_intelligence_comparison,
)
from app.internal_alpha.intelligence.receipt import build_intelligence_receipt


def _entry(candidate: str, active_testers: int = 1) -> dict[str, object]:
    report: dict[str, object] = {
        "schema": "lionsforge.internal-alpha-intelligence-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "metrics": {"active_testers": active_testers},
        "readiness": {"state": "READY"},
        "repeated_categories": [],
        "blocking_reasons": [],
        "interpretation_notice": "bounded",
    }
    return {"report": report, "receipt": build_intelligence_receipt(report)}


def _comparison() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    baseline = build_intelligence_bundle([_entry("a" * 40), _entry("b" * 40)])
    candidate = build_intelligence_bundle(
        [_entry("b" * 40, active_testers=2), _entry("c" * 40)]
    )
    return compare_intelligence_bundles(baseline, candidate), baseline, candidate


def test_reports_added_removed_changed_and_unchanged_candidates() -> None:
    result, baseline, candidate = _comparison()

    assert result["added_candidates"] == ["c" * 40]
    assert result["removed_candidates"] == ["a" * 40]
    assert result["changed_candidates"] == ["b" * 40]
    assert result["unchanged_candidate_count"] == 0
    assert len(result["comparison_sha256"]) == 64
    assert validate_intelligence_comparison(result, baseline, candidate) == []


def test_is_deterministic_and_counts_unchanged_candidates() -> None:
    baseline = build_intelligence_bundle([_entry("a" * 40), _entry("b" * 40)])
    candidate = copy.deepcopy(baseline)

    first = compare_intelligence_bundles(baseline, candidate)
    second = compare_intelligence_bundles(baseline, candidate)

    assert first == second
    assert first["added_candidates"] == []
    assert first["removed_candidates"] == []
    assert first["changed_candidates"] == []
    assert first["unchanged_candidate_count"] == 2


def test_rejects_invalid_baseline_or_candidate_bundle() -> None:
    valid = build_intelligence_bundle([_entry("a" * 40)])
    invalid = copy.deepcopy(valid)
    invalid["bundle_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="invalid baseline bundle"):
        compare_intelligence_bundles(invalid, valid)
    with pytest.raises(ValueError, match="invalid candidate bundle"):
        compare_intelligence_bundles(valid, invalid)


def test_validation_rejects_extra_fields_and_coercive_counts() -> None:
    comparison, baseline, candidate = _comparison()

    extra = {**comparison, "extra": "field"}
    findings = validate_intelligence_comparison(extra, baseline, candidate)
    assert "comparison fields mismatch" in findings
    assert "comparison payload mismatch" in findings

    coercive = {**comparison, "unchanged_candidate_count": False}
    findings = validate_intelligence_comparison(coercive, baseline, candidate)
    assert "invalid unchanged candidate count" in findings

    coercive_version = {**comparison, "schema_version": True}
    findings = validate_intelligence_comparison(coercive_version, baseline, candidate)
    assert "unsupported comparison schema version" in findings


def test_validation_rejects_noncanonical_digests_and_candidate_lists() -> None:
    comparison, baseline, candidate = _comparison()

    uppercase_digest = {**comparison, "comparison_sha256": "A" * 64}
    findings = validate_intelligence_comparison(uppercase_digest, baseline, candidate)
    assert "invalid comparison digest" in findings
    assert "comparison digest mismatch" in findings

    malformed_binding = {**comparison, "baseline_bundle_sha256": 7}
    findings = validate_intelligence_comparison(malformed_binding, baseline, candidate)
    assert "invalid baseline bundle digest" in findings
    assert "baseline bundle digest binding mismatch" in findings

    unsorted = {**comparison, "added_candidates": ["f" * 40, "c" * 40]}
    findings = validate_intelligence_comparison(unsorted, baseline, candidate)
    assert "invalid added candidate list" in findings
    assert "comparison payload mismatch" in findings

    duplicate = {**comparison, "removed_candidates": ["a" * 40, "a" * 40]}
    findings = validate_intelligence_comparison(duplicate, baseline, candidate)
    assert "invalid removed candidate list" in findings

    malformed = {**comparison, "changed_candidates": ["NOT_A_SHA"]}
    findings = validate_intelligence_comparison(malformed, baseline, candidate)
    assert "invalid changed candidate list" in findings
