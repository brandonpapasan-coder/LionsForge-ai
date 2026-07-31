from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.bundle import (
    build_intelligence_bundle,
    validate_intelligence_bundle,
)
from app.internal_alpha.intelligence.comparison import (
    compare_intelligence_bundles,
    validate_intelligence_comparison,
)
from app.internal_alpha.intelligence.comparison_archive import (
    build_intelligence_comparison_archive,
    validate_intelligence_comparison_archive,
)
from app.internal_alpha.intelligence.comparison_receipt import (
    build_intelligence_comparison_receipt,
    validate_intelligence_comparison_receipt,
)
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


class IntelligenceBundleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    entries: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class IntelligenceBundleValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    bundle: dict[str, Any]


class IntelligenceComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    baseline: dict[str, Any]
    candidate: dict[str, Any]


class IntelligenceComparisonValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    comparison: dict[str, Any]
    baseline: dict[str, Any]
    candidate: dict[str, Any]


class IntelligenceComparisonReceiptInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    comparison: dict[str, Any]
    baseline: dict[str, Any]
    candidate: dict[str, Any]


class IntelligenceComparisonReceiptValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    receipt: dict[str, Any]
    comparison: dict[str, Any]
    baseline: dict[str, Any]
    candidate: dict[str, Any]


class IntelligenceComparisonArchiveInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    baseline: dict[str, Any]
    candidate: dict[str, Any]
    comparison: dict[str, Any]
    receipt: dict[str, Any]


class IntelligenceComparisonArchiveValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    archive: dict[str, Any]


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
    del current_user
    report = _serialize_report(payload)
    return {"report": report, "receipt": build_intelligence_receipt(report)}


@router.post("/report/validate")
def validate_internal_alpha_intelligence_report(
    payload: IntelligenceReceiptValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
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


@router.post("/bundle")
def create_internal_alpha_intelligence_bundle(
    payload: IntelligenceBundleInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return build_intelligence_bundle(payload.entries)


@router.post("/bundle/validate")
def validate_internal_alpha_intelligence_bundle(
    payload: IntelligenceBundleValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    findings = validate_intelligence_bundle(payload.bundle)
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Bundle validity proves bounded payload integrity only and does not authorize public beta, "
            "production deployment, or general availability."
        ),
    }


@router.post("/comparison")
def create_internal_alpha_intelligence_comparison(
    payload: IntelligenceComparisonInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return compare_intelligence_bundles(payload.baseline, payload.candidate)


@router.post("/comparison/validate")
def validate_internal_alpha_intelligence_comparison(
    payload: IntelligenceComparisonValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    findings = validate_intelligence_comparison(
        payload.comparison,
        payload.baseline,
        payload.candidate,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Comparison validity proves deterministic payload binding only and does not infer "
            "causality or authorize any release transition."
        ),
    }


@router.post("/comparison/receipt")
def create_internal_alpha_intelligence_comparison_receipt(
    payload: IntelligenceComparisonReceiptInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return build_intelligence_comparison_receipt(
        payload.comparison,
        payload.baseline,
        payload.candidate,
    )


@router.post("/comparison/receipt/validate")
def validate_internal_alpha_intelligence_comparison_receipt(
    payload: IntelligenceComparisonReceiptValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    findings = validate_intelligence_comparison_receipt(
        payload.receipt,
        payload.comparison,
        payload.baseline,
        payload.candidate,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Receipt validity proves deterministic comparison verification only and does not "
            "infer causality or authorize any release transition."
        ),
    }


@router.post("/comparison/archive")
def create_internal_alpha_intelligence_comparison_archive(
    payload: IntelligenceComparisonArchiveInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Package one fully validated comparison receipt chain."""
    del current_user
    return build_intelligence_comparison_archive(
        payload.baseline,
        payload.candidate,
        payload.comparison,
        payload.receipt,
    )


@router.post("/comparison/archive/validate")
def validate_internal_alpha_intelligence_comparison_archive(
    payload: IntelligenceComparisonArchiveValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate a self-contained comparison archive fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive(payload.archive)
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Archive validity proves deterministic evidence preservation only and does not infer "
            "causality or authorize any release transition."
        ),
    }
