import copy

import pytest

from app.internal_alpha.intelligence.bundle import build_intelligence_bundle
from app.internal_alpha.intelligence.comparison import compare_intelligence_bundles
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


def test_reports_added_removed_changed_and_unchanged_candidates() -> None:
    baseline = build_intelligence_bundle([_entry("a" * 40), _entry("b" * 40)])
    candidate = build_intelligence_bundle(
        [_entry("b" * 40, active_testers=2), _entry("c" * 40)]
    )

    result = compare_intelligence_bundles(baseline, candidate)

    assert result["added_candidates"] == ["c" * 40]
    assert result["removed_candidates"] == ["a" * 40]
    assert result["changed_candidates"] == ["b" * 40]
    assert result["unchanged_candidate_count"] == 0
    assert len(result["comparison_sha256"]) == 64


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
