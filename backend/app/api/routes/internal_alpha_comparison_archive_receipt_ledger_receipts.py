from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt import (
    build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt,
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt,
)
from app.models.user import User

router = APIRouter()


class IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerReceiptInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ledger: dict[str, Any]


class IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerReceiptValidationInput(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)

    receipt: dict[str, Any]
    ledger: dict[str, Any]


@router.post("/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt")
def create_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
    payload: IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerReceiptInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issue a compact receipt for one fully validated bundle-receipt ledger."""
    del current_user
    return build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        payload.ledger
    )


@router.post("/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/validate")
def validate_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
    payload: IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerReceiptValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate a ledger receipt and its exact ledger binding fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        payload.receipt,
        payload.ledger,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Ledger receipt validity proves deterministic bounded evidence-ledger verification "
            "only. It does not infer causality or authorize any release transition."
        ),
    }
