from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest import (
    build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest,
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest,
)
from app.models.user import User

router = APIRouter()


class IntelligenceComparisonArchiveReceiptLedgerReceiptManifestVerificationReceiptManifestInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    entries: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class IntelligenceComparisonArchiveReceiptLedgerReceiptManifestVerificationReceiptManifestValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    manifest: dict[str, Any]


@router.post(
    "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest"
)
def create_internal_alpha_intelligence_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest(
    payload: IntelligenceComparisonArchiveReceiptLedgerReceiptManifestVerificationReceiptManifestInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Build one bounded deterministic manifest from validated verification receipts."""
    del current_user
    return build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        payload.entries
    )


@router.post(
    "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest/validate"
)
def validate_internal_alpha_intelligence_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest(
    payload: IntelligenceComparisonArchiveReceiptLedgerReceiptManifestVerificationReceiptManifestValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate one bounded verification-receipt manifest fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        payload.manifest
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Manifest validity proves deterministic bounded verification-receipt collation only. "
            "It does not infer causality or authorize any release transition."
        ),
    }
