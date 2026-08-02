from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt import (
    build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt,
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt,
)
from app.models.user import User

router = APIRouter()


class IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)

    manifest: dict[str, Any]


class IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)

    receipt: dict[str, Any]
    manifest: dict[str, Any]


@router.post(
    "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest/verification-receipt"
)
def create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
    payload: IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issue one deterministic receipt for a valid verification-receipt manifest."""
    del current_user
    return build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        payload.manifest
    )


@router.post(
    "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest/verification-receipt/validate"
)
def validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
    payload: IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate one receipt and its exact source-manifest binding fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        payload.receipt,
        payload.manifest,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Receipt validity proves deterministic bounded verification-receipt manifest "
            "verification only. It does not infer causality or authorize any release transition."
        ),
    }
