from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_receipt_manifest import (
    build_intelligence_comparison_archive_receipt_manifest,
    validate_intelligence_comparison_archive_receipt_manifest,
)
from app.models.user import User

router = APIRouter()


class IntelligenceComparisonArchiveReceiptManifestInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    entries: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class IntelligenceComparisonArchiveReceiptManifestValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    manifest: dict[str, Any]


@router.post("/comparison/archive/receipt/manifest")
def create_internal_alpha_intelligence_comparison_archive_receipt_manifest(
    payload: IntelligenceComparisonArchiveReceiptManifestInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Build one bounded manifest from validated comparison archive receipts."""
    del current_user
    return build_intelligence_comparison_archive_receipt_manifest(payload.entries)


@router.post("/comparison/archive/receipt/manifest/validate")
def validate_internal_alpha_intelligence_comparison_archive_receipt_manifest(
    payload: IntelligenceComparisonArchiveReceiptManifestValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate one archive-receipt manifest fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive_receipt_manifest(payload.manifest)
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Manifest validity proves bounded evidence packaging and transfer integrity only. "
            "It does not infer causality or authorize any release transition."
        ),
    }
