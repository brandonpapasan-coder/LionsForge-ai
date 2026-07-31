from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_receipt import (
    build_intelligence_comparison_archive_receipt,
    validate_intelligence_comparison_archive_receipt,
)
from app.models.user import User

router = APIRouter()


class IntelligenceComparisonArchiveReceiptInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    archive: dict[str, Any]


class IntelligenceComparisonArchiveReceiptValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    receipt: dict[str, Any]
    archive: dict[str, Any]


@router.post("/comparison/archive/receipt")
def create_internal_alpha_intelligence_comparison_archive_receipt(
    payload: IntelligenceComparisonArchiveReceiptInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issue a compact receipt for one fully validated comparison archive."""
    del current_user
    return build_intelligence_comparison_archive_receipt(payload.archive)


@router.post("/comparison/archive/receipt/validate")
def validate_internal_alpha_intelligence_comparison_archive_receipt(
    payload: IntelligenceComparisonArchiveReceiptValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate an archive receipt and its exact archive binding fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive_receipt(
        payload.receipt,
        payload.archive,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Archive receipt validity proves deterministic archive verification only and does "
            "not infer causality or authorize any release transition."
        ),
    }
