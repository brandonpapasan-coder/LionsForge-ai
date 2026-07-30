import copy

import pytest
from pydantic import ValidationError

from app.api.routes.internal_alpha_intelligence import (
    IntelligenceBundleInput,
    IntelligenceBundleValidationInput,
    IntelligenceReceiptValidationInput,
    IntelligenceReportInput,
    create_internal_alpha_intelligence_bundle,
    create_internal_alpha_intelligence_report,
    validate_internal_alpha_intelligence_bundle,
    validate_internal_alpha_intelligence_report,
)


CANDIDATE = "a" * 40


def _payload(**changes: object) -> IntelligenceReportInput:
    values: dict[str, object] = {
        "candidate_sha": CANDIDATE,
        "metrics": {
            "active_testers": 5,
            "active_experiments": 2,
            "feedback_items": 8,
            "completed_experiments": 1,
        },
        "readiness": {
            "security": 95.0,
            "reliability": 94.0,
            "feedback": 92.0,
            "regression": 96.0,
        },
        "repeated_categories": {"USABILITY": 3, "PERFORMANCE": 2},
    }
    values.update(changes)
    return IntelligenceReportInput.model_validate(values)


def test_builds_authenticated_candidate_bound_report_and_receipt() -> None:
    result = create_internal_alpha_intelligence_report(_payload(), current_user=object())  # type: ignore[arg-type]
    report = result["report"]
    receipt = result["receipt"]
    assert report["schema"] == "lionsforge.internal-alpha-intelligence-report"
    assert report["candidate_sha"] == CANDIDATE
    assert report["readiness"]["state"] == "READY"
    assert report["blocking_reasons"] == []
    assert receipt["schema"] == "lionsforge.internal-alpha-intelligence-receipt"
    assert receipt["candidate_sha"] == CANDIDATE
    assert len(receipt["report_sha256"]) == 64


def test_validates_receipt_and_rejects_report_drift() -> None:
    created = create_internal_alpha_intelligence_report(_payload(), current_user=object())  # type: ignore[arg-type]
    valid = validate_internal_alpha_intelligence_report(
        IntelligenceReceiptValidationInput.model_validate(created),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert valid["valid"] is True
    assert valid["findings"] == []

    drifted = {**created["report"], "blocking_reasons": ["SUBSTITUTED"]}
    invalid = validate_internal_alpha_intelligence_report(
        IntelligenceReceiptValidationInput.model_validate(
            {"report": drifted, "receipt": created["receipt"]}
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert invalid["valid"] is False
    assert invalid["findings"] == ["report digest mismatch"]


def test_builds_and_validates_authenticated_bundle() -> None:
    first = create_internal_alpha_intelligence_report(_payload(candidate_sha="b" * 40), current_user=object())  # type: ignore[arg-type]
    second = create_internal_alpha_intelligence_report(_payload(candidate_sha="a" * 40), current_user=object())  # type: ignore[arg-type]
    bundle = create_internal_alpha_intelligence_bundle(
        IntelligenceBundleInput.model_validate({"entries": [first, second]}),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert bundle["entry_count"] == 2
    assert bundle["entries"][0]["report"]["candidate_sha"] == "a" * 40

    result = validate_internal_alpha_intelligence_bundle(
        IntelligenceBundleValidationInput.model_validate({"bundle": bundle}),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert result["valid"] is True
    assert result["findings"] == []
    assert "does not authorize" in result["interpretation_notice"]


def test_bundle_validation_rejects_drift() -> None:
    created = create_internal_alpha_intelligence_report(_payload(), current_user=object())  # type: ignore[arg-type]
    bundle = create_internal_alpha_intelligence_bundle(
        IntelligenceBundleInput.model_validate({"entries": [created]}),
        current_user=object(),  # type: ignore[arg-type]
    )
    drifted = copy.deepcopy(bundle)
    drifted["bundle_sha256"] = "0" * 64
    result = validate_internal_alpha_intelligence_bundle(
        IntelligenceBundleValidationInput.model_validate({"bundle": drifted}),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert result["valid"] is False
    assert result["findings"] == ["bundle digest mismatch"]


def test_emits_fail_closed_blockers() -> None:
    payload = _payload(
        metrics={
            "active_testers": 1,
            "active_experiments": 0,
            "feedback_items": 0,
            "completed_experiments": 0,
        },
        readiness={
            "security": 100.0,
            "reliability": 100.0,
            "feedback": 70.0,
            "regression": 100.0,
        },
        repeated_categories={"DEFECT": 2},
    )
    result = create_internal_alpha_intelligence_report(payload, current_user=object())  # type: ignore[arg-type]
    assert result["report"]["blocking_reasons"] == [
        "NO_ACTIVE_EXPERIMENTS",
        "NO_FEEDBACK_EVIDENCE",
        "READINESS_GUARDRAIL_NOT_MET",
        "REPEATED_DEFECT_SIGNAL",
    ]


def test_rejects_extra_fields_boolean_counts_and_invalid_sha() -> None:
    with pytest.raises(ValidationError):
        IntelligenceReportInput.model_validate(
            {**_payload().model_dump(), "candidate_sha": "not-a-sha"}
        )
    with pytest.raises(ValidationError):
        IntelligenceReportInput.model_validate(
            {
                **_payload().model_dump(),
                "metrics": {
                    **_payload().metrics.model_dump(),
                    "active_testers": True,
                },
            }
        )
    with pytest.raises(ValidationError):
        IntelligenceReportInput.model_validate(
            {**_payload().model_dump(), "unexpected": "private-free-form-data"}
        )
    with pytest.raises(ValidationError):
        IntelligenceBundleInput.model_validate({"entries": []})


@pytest.mark.parametrize(
    "repeated_categories",
    [
        {"OTHER": 2},
        {"DEFECT": 1},
        {"DEFECT": True},
        {"DEFECT": 10_001},
    ],
)
def test_rejects_invalid_repeated_categories(repeated_categories: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        IntelligenceReportInput.model_validate(
            {**_payload().model_dump(), "repeated_categories": repeated_categories}
        )
