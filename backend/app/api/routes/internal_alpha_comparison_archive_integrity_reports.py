from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_integrity_report import (
    build_intelligence_comparison_archive_integrity_report,
    validate_intelligence_comparison_archive_integrity_report,
)
from app.models.user import User

router = APIRouter()


class IntelligenceComparisonArchiveIntegrityReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    receipt: dict[str, Any]
    manifest: dict[str, Any]


class IntelligenceComparisonArchiveIntegrityReportValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    report: dict[str, Any]
    receipt: dict[str, Any]
    manifest: dict[str, Any]


@router.post("/comparison/archive/integrity-report")
def create_internal_alpha_intelligence_comparison_archive_integrity_report(
    payload: IntelligenceComparisonArchiveIntegrityReportInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create one deterministic integrity report for an exact valid receipt-manifest pair."""
    del current_user
    return build_intelligence_comparison_archive_integrity_report(
        payload.receipt,
        payload.manifest,
    )


@router.post("/comparison/archive/integrity-report/validate")
def validate_internal_alpha_intelligence_comparison_archive_integrity_report(
    payload: IntelligenceComparisonArchiveIntegrityReportValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate one report and its exact source bindings fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report(
        payload.report,
        payload.receipt,
        payload.manifest,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Report validity summarizes deterministic receipt-chain integrity only. "
            "It does not infer causality or authorize any release transition."
        ),
    }
