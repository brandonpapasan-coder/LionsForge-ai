from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt import (
    build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt,
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt,
)
from app.models.user import User

router = APIRouter()

_MAX_FINDINGS = 100
_MAX_FINDING_LENGTH = 256
_TRUNCATED_FINDINGS_NOTICE = "additional validation findings omitted"
_VALIDATION_FAILURE_FINDING = "verification receipt manifest validation failed"


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


def _bounded_findings(findings: list[str]) -> list[str]:
    if len(findings) <= _MAX_FINDINGS:
        return [finding[:_MAX_FINDING_LENGTH] for finding in findings]

    bounded = [
        finding[:_MAX_FINDING_LENGTH]
        for finding in findings[: _MAX_FINDINGS - 1]
    ]
    bounded.append(_TRUNCATED_FINDINGS_NOTICE)
    return bounded


@router.post(
    "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest/verification-receipt"
)
def create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
    payload: IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issue one deterministic receipt for a valid verification-receipt manifest."""
    del current_user
    try:
        return build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
            payload.manifest
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid verification receipt manifest",
        ) from exc


@router.post(
    "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest/verification-receipt/validate"
)
def validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
    payload: IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate one receipt and its exact source-manifest binding fail closed."""
    del current_user
    try:
        findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
            payload.receipt,
            payload.manifest,
        )
    except (TypeError, ValueError):
        findings = [_VALIDATION_FAILURE_FINDING]
    return {
        "valid": not findings,
        "findings": _bounded_findings(findings),
        "interpretation_notice": (
            "Receipt validity proves deterministic bounded verification-receipt manifest "
            "verification only. It does not infer causality or authorize any release transition."
        ),
    }
