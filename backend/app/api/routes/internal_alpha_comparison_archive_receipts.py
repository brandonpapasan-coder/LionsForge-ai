from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_receipt import (
    build_intelligence_comparison_archive_receipt,
    validate_intelligence_comparison_archive_receipt,
)
from app.internal_alpha.intelligence.comparison_archive_receipt_manifest import (
    build_intelligence_comparison_archive_receipt_manifest,
    validate_intelligence_comparison_archive_receipt_manifest,
)
from app.internal_alpha.intelligence.comparison_archive_receipt_manifest_bundle import (
    build_intelligence_comparison_archive_receipt_manifest_bundle,
    validate_intelligence_comparison_archive_receipt_manifest_bundle,
)
from app.internal_alpha.intelligence.comparison_archive_receipt_manifest_receipt import (
    build_intelligence_comparison_archive_receipt_manifest_receipt,
    validate_intelligence_comparison_archive_receipt_manifest_receipt,
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


class IntelligenceComparisonArchiveReceiptManifestInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    entries: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class IntelligenceComparisonArchiveReceiptManifestValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    manifest: dict[str, Any]


class IntelligenceComparisonArchiveReceiptManifestReceiptInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    manifest: dict[str, Any]


class IntelligenceComparisonArchiveReceiptManifestReceiptValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    receipt: dict[str, Any]
    manifest: dict[str, Any]


class IntelligenceComparisonArchiveReceiptManifestBundleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    manifest: dict[str, Any]
    receipt: dict[str, Any]


class IntelligenceComparisonArchiveReceiptManifestBundleValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    bundle: dict[str, Any]


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


@router.post("/comparison/archive/receipt/manifest/receipt")
def create_internal_alpha_intelligence_comparison_archive_receipt_manifest_receipt(
    payload: IntelligenceComparisonArchiveReceiptManifestReceiptInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issue a compact receipt for one fully validated archive-receipt manifest."""
    del current_user
    return build_intelligence_comparison_archive_receipt_manifest_receipt(payload.manifest)


@router.post("/comparison/archive/receipt/manifest/receipt/validate")
def validate_internal_alpha_intelligence_comparison_archive_receipt_manifest_receipt(
    payload: IntelligenceComparisonArchiveReceiptManifestReceiptValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate a manifest receipt and its exact manifest binding fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive_receipt_manifest_receipt(
        payload.receipt,
        payload.manifest,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Manifest receipt validity proves deterministic batch evidence verification only. "
            "It does not infer causality or authorize any release transition."
        ),
    }


@router.post("/comparison/archive/receipt/manifest/bundle")
def create_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle(
    payload: IntelligenceComparisonArchiveReceiptManifestBundleInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Build one deterministic transport bundle from an exact manifest-receipt chain."""
    del current_user
    return build_intelligence_comparison_archive_receipt_manifest_bundle(
        payload.manifest,
        payload.receipt,
    )


@router.post("/comparison/archive/receipt/manifest/bundle/validate")
def validate_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle(
    payload: IntelligenceComparisonArchiveReceiptManifestBundleValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate a manifest transport bundle and its complete chain fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle(payload.bundle)
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Bundle validity proves deterministic evidence transfer integrity only. It does not "
            "infer causality or authorize any release transition."
        ),
    }
