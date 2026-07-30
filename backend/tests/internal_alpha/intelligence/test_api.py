import pytest
from pydantic import ValidationError

from app.api.routes.internal_alpha_intelligence import (
    IntelligenceReportInput,
    create_internal_alpha_intelligence_report,
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


def test_builds_authenticated_candidate_bound_report() -> None:
    result = create_internal_alpha_intelligence_report(_payload(), current_user=object())  # type: ignore[arg-type]
    assert result["schema"] == "lionsforge.internal-alpha-intelligence-report"
    assert result["schema_version"] == 1
    assert result["candidate_sha"] == CANDIDATE
    assert result["readiness"]["state"] == "READY"
    assert result["blocking_reasons"] == []
    assert result["repeated_categories"] == [
        {"category": "USABILITY", "count": 3},
        {"category": "PERFORMANCE", "count": 2},
    ]
    assert "does not authorize" in result["interpretation_notice"]


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
    assert result["blocking_reasons"] == [
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
