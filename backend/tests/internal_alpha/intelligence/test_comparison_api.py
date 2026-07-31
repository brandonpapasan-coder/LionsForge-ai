import copy

import pytest
from pydantic import ValidationError

from app.api.routes.internal_alpha_intelligence import (
    IntelligenceBundleInput,
    IntelligenceComparisonInput,
    IntelligenceComparisonValidationInput,
    IntelligenceReportInput,
    create_internal_alpha_intelligence_bundle,
    create_internal_alpha_intelligence_comparison,
    create_internal_alpha_intelligence_report,
    validate_internal_alpha_intelligence_comparison,
)


def _report_input(candidate_sha: str, *, feedback_items: int = 8) -> IntelligenceReportInput:
    return IntelligenceReportInput.model_validate(
        {
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
            },
            "repeated_categories": {},
        }
    )


def _entry(candidate_sha: str, *, feedback_items: int = 8) -> dict[str, object]:
    return create_internal_alpha_intelligence_report(
        _report_input(candidate_sha, feedback_items=feedback_items),
        current_user=object(),  # type: ignore[arg-type]
    )


def _bundle(*entries: dict[str, object]) -> dict[str, object]:
    return create_internal_alpha_intelligence_bundle(
        IntelligenceBundleInput.model_validate({"entries": list(entries)}),
        current_user=object(),  # type: ignore[arg-type]
    )


def test_creates_authenticated_digest_bound_comparison() -> None:
    baseline = _bundle(_entry("a" * 40), _entry("b" * 40))
    candidate = _bundle(
        _entry("a" * 40, feedback_items=9),
        _entry("c" * 40),
    )

    comparison = create_internal_alpha_intelligence_comparison(
        IntelligenceComparisonInput.model_validate(
            {"baseline": baseline, "candidate": candidate}
        ),
        current_user=object(),  # type: ignore[arg-type]
    )

    assert comparison["baseline_bundle_sha256"] == baseline["bundle_sha256"]
    assert comparison["candidate_bundle_sha256"] == candidate["bundle_sha256"]
    assert comparison["added_candidates"] == ["c" * 40]
    assert comparison["removed_candidates"] == ["b" * 40]
    assert comparison["changed_candidates"] == ["a" * 40]
    assert comparison["unchanged_candidate_count"] == 0
    assert len(comparison["comparison_sha256"]) == 64


def test_validates_comparison_and_rejects_payload_drift() -> None:
    baseline = _bundle(_entry("a" * 40))
    candidate = _bundle(_entry("a" * 40, feedback_items=9))
    comparison = create_internal_alpha_intelligence_comparison(
        IntelligenceComparisonInput.model_validate(
            {"baseline": baseline, "candidate": candidate}
        ),
        current_user=object(),  # type: ignore[arg-type]
    )

    valid = validate_internal_alpha_intelligence_comparison(
        IntelligenceComparisonValidationInput.model_validate(
            {
                "comparison": comparison,
                "baseline": baseline,
                "candidate": candidate,
            }
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert valid["valid"] is True
    assert valid["findings"] == []

    drifted = copy.deepcopy(comparison)
    drifted["changed_candidates"] = []
    invalid = validate_internal_alpha_intelligence_comparison(
        IntelligenceComparisonValidationInput.model_validate(
            {
                "comparison": drifted,
                "baseline": baseline,
                "candidate": candidate,
            }
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert invalid["valid"] is False
    assert invalid["findings"] == ["comparison payload mismatch"]


def test_rejects_substituted_candidate_bundle_and_extra_fields() -> None:
    baseline = _bundle(_entry("a" * 40))
    candidate = _bundle(_entry("b" * 40))
    comparison = create_internal_alpha_intelligence_comparison(
        IntelligenceComparisonInput.model_validate(
            {"baseline": baseline, "candidate": candidate}
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    substituted = _bundle(_entry("c" * 40))

    result = validate_internal_alpha_intelligence_comparison(
        IntelligenceComparisonValidationInput.model_validate(
            {
                "comparison": comparison,
                "baseline": baseline,
                "candidate": substituted,
            }
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert result["valid"] is False
    assert "candidate bundle digest binding mismatch" in result["findings"]
    assert "comparison digest mismatch" in result["findings"]

    with pytest.raises(ValidationError):
        IntelligenceComparisonInput.model_validate(
            {
                "baseline": baseline,
                "candidate": candidate,
                "unexpected": "free-form-data",
            }
        )
