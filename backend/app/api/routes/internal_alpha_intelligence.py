from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.dashboard_metrics import build_metrics
from app.internal_alpha.intelligence.feedback_analyzer import VALID_CATEGORIES
from app.internal_alpha.intelligence.readiness_score import calculate_readiness_score
from app.internal_alpha.intelligence.receipt import (
    build_intelligence_receipt,
    validate_intelligence_receipt,
)
from app.internal_alpha.intelligence.report import build_intelligence_report
from app.models.user import User

router = APIRouter()


class MetricsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    active_testers: int = Field(ge=0, le=1_000_000)
    active_experiments: int = Field(ge=0, le=1_000_000)
    feedback_items: int = Field(ge=0, le=1_000_000)
    completed_experiments: int = Field(ge=0, le=1_000_000)


class ReadinessInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    security: float = Field(ge=0, le=100)
    reliability: float = Field(ge=0, le=100)
    feedback: float = Field(ge=0, le=100)
    regression: float = Field(ge=0, le=100)


class IntelligenceReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    candidate_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    metrics: MetricsInput
    readiness: ReadinessInput
    repeated_categories: dict[str, int] = Field(default_factory=dict, max_length=5)

    @field_validator("repeated_categories")
    @classmethod
    def validate_repeated_categories(cls, value: dict[str, int]) -> dict[str, int]:
        if any(category not in VALID_CATEGORIES for category in value):
            raise ValueError("repeated_categories contains an invalid category")
        if any(isinstance(count, bool) or not isinstance(count, int) for count in value.values()):
            raise TypeError("repeated category counts must be integers")
        if any(not 2 <= count <= 10_000 for count in value.values()):
            raise ValueError("repeated category counts must be between 2 and 10000")
        return value


class IntelligenceReceiptValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    report: dict[str, Any]
    receipt: dict[str, Any]


def _serialize_report(payload: IntelligenceReportInput) -> dict[str, Any]:
    metrics = build_metrics(**payload.metrics.model_dump())
    readiness = calculate_readiness_score(**payload.readiness.model_dump())
    report = build_intelligence_report(
        candidate_sha=payload.candidate_sha,
        metrics=metrics,
        readiness=readiness,
        repeated_categories=payload.repeated_categories,
    )
    return {
        "schema": "lionsforge.internal-alpha-intelligence-report",
        "schema_version": 1,
        "candidate_sha": report.candidate_sha,
        "metrics": {
            "active_testers": report.metrics.active_testers,
            "active_experiments": report.metrics.active_experiments,
            "feedback_items": report.metrics.feedback_items,
            "completed_experiments": report.metrics.completed_experiments,
        },
        "readiness": {
            "security": report.readiness.security,
            "reliability": report.readiness.reliability,
            "feedback": report.readiness.feedback,
            "regression": report.readiness.regression,
            "overall": report.readiness.overall,
            "state": report.readiness.state,
        },
        "repeated_categories": [
            {"category": category, "count": count}
            for category, count in report.repeated_categories
        ],
        "blocking_reasons": list(report.blocking_reasons),
        "interpretation_notice": (
            "This report summarizes bounded internal-alpha evidence and does not authorize "
            "public beta, production deployment, or general availability."
        ),
    }


@router.post("/report")
def create_internal_alpha_intelligence_report(
    payload: IntelligenceReportInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return one candidate-bound report with a deterministic integrity receipt."""
    del current_user
    report = _serialize_report(payload)
    return {"report": report, "receipt": build_intelligence_receipt(report)}


@router.post("/report/validate")
def validate_internal_alpha_intelligence_report(
    payload: IntelligenceReceiptValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate report integrity without authorizing any release transition."""
    del current_user
    findings = validate_intelligence_receipt(payload.receipt, payload.report)
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Receipt validity proves payload integrity only and does not authorize public beta, "
            "production deployment, or general availability."
        ),
    }
