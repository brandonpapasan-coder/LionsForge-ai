import copy

import pytest

from app.internal_alpha.intelligence.bundle import (
    build_intelligence_bundle,
    validate_intelligence_bundle,
)
from app.internal_alpha.intelligence.receipt import build_intelligence_receipt


def _report(candidate: str) -> dict[str, object]:
    return {
        "schema": "lionsforge.internal-alpha-intelligence-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "metrics": {"active_testers": 1},
        "readiness": {"state": "READY"},
        "repeated_categories": [],
        "blocking_reasons": [],
        "interpretation_notice": "bounded",
    }


def _entry(candidate: str) -> dict[str, object]:
    report = _report(candidate)
    return {"report": report, "receipt": build_intelligence_receipt(report)}


def test_builds_canonically_ordered_deterministic_bundle() -> None:
    bundle = build_intelligence_bundle([_entry("b" * 40), _entry("a" * 40)])
    assert bundle["entry_count"] == 2
    assert [entry["report"]["candidate_sha"] for entry in bundle["entries"]] == [
        "a" * 40,
        "b" * 40,
    ]
    assert len(bundle["bundle_sha256"]) == 64
    assert validate_intelligence_bundle(bundle) == []


def test_rejects_duplicate_candidates_and_invalid_receipts() -> None:
    with pytest.raises(ValueError, match="unique"):
        build_intelligence_bundle([_entry("a" * 40), _entry("a" * 40)])

    invalid = _entry("a" * 40)
    invalid["receipt"]["report_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="invalid bundle entry"):
        build_intelligence_bundle([invalid])


def test_validation_detects_drift_count_and_order() -> None:
    bundle = build_intelligence_bundle([_entry("a" * 40), _entry("b" * 40)])

    drifted = copy.deepcopy(bundle)
    drifted["entries"][0]["report"]["metrics"]["active_testers"] = 9
    assert "invalid bundle entries" in validate_intelligence_bundle(drifted)

    wrong_count = copy.deepcopy(bundle)
    wrong_count["entry_count"] = 99
    assert "bundle entry count mismatch" in validate_intelligence_bundle(wrong_count)

    reversed_bundle = copy.deepcopy(bundle)
    reversed_bundle["entries"].reverse()
    findings = validate_intelligence_bundle(reversed_bundle)
    assert "bundle entries are not canonically ordered" in findings
    assert "bundle digest mismatch" not in findings


def test_rejects_unbounded_or_malformed_entries() -> None:
    with pytest.raises(ValueError, match="between 1 and 100"):
        build_intelligence_bundle([])
    with pytest.raises(ValueError, match="only report and receipt"):
        build_intelligence_bundle([{"report": {}, "receipt": {}, "extra": {}}])


def test_validation_rejects_extra_fields_and_coercive_scalars() -> None:
    bundle = build_intelligence_bundle([_entry("a" * 40)])

    extra = {**bundle, "unexpected": "private-free-form-data"}
    assert validate_intelligence_bundle(extra) == ["bundle fields are invalid"]

    boolean_version = {**bundle, "schema_version": True}
    assert "unsupported bundle schema version" in validate_intelligence_bundle(
        boolean_version
    )

    boolean_count = {**bundle, "entry_count": True}
    findings = validate_intelligence_bundle(boolean_count)
    assert "bundle entry count is invalid" in findings
    assert "bundle entry count mismatch" not in findings


def test_validation_rejects_noncanonical_digest_values() -> None:
    bundle = build_intelligence_bundle([_entry("a" * 40)])

    uppercase = {**bundle, "bundle_sha256": bundle["bundle_sha256"].upper()}
    findings = validate_intelligence_bundle(uppercase)
    assert "bundle digest is invalid" in findings
    assert "bundle digest mismatch" in findings

    non_hex = {**bundle, "bundle_sha256": "g" * 64}
    findings = validate_intelligence_bundle(non_hex)
    assert "bundle digest is invalid" in findings
    assert "bundle digest mismatch" in findings

    boolean_digest = {**bundle, "bundle_sha256": True}
    findings = validate_intelligence_bundle(boolean_digest)
    assert "bundle digest is invalid" in findings
    assert "bundle digest mismatch" in findings


def test_validation_rejects_invalid_entry_collection_bounds() -> None:
    bundle = build_intelligence_bundle([_entry("a" * 40)])

    empty = {**bundle, "entry_count": 0, "entries": []}
    findings = validate_intelligence_bundle(empty)
    assert "bundle entry count is invalid" in findings
    assert "invalid bundle entries" in findings

    not_a_list = {**bundle, "entries": {}}
    assert "bundle entries must be a list" in validate_intelligence_bundle(not_a_list)
