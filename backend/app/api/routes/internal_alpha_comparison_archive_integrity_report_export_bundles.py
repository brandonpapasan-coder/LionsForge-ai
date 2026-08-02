from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_bundle import (
    build_intelligence_comparison_archive_integrity_report_export_bundle,
    serialize_intelligence_comparison_archive_integrity_report_export_bundle,
    validate_intelligence_comparison_archive_integrity_report_export_bundle,
)
from app.models.user import User

router = APIRouter()


class IntelligenceComparisonArchiveIntegrityReportExportBundleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    report: dict[str, Any]
    receipt: dict[str, Any]
    manifest: dict[str, Any]


class IntelligenceComparisonArchiveIntegrityReportExportBundleValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    bundle: dict[str, Any]


@router.post("/comparison/archive/integrity-report/export-bundle")
def create_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
    payload: IntelligenceComparisonArchiveIntegrityReportExportBundleInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create one deterministic portable bundle for an exact valid report chain."""
    del current_user
    return build_intelligence_comparison_archive_integrity_report_export_bundle(
        payload.report,
        payload.receipt,
        payload.manifest,
    )


@router.post("/comparison/archive/integrity-report/export-bundle/validate")
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
    payload: IntelligenceComparisonArchiveIntegrityReportExportBundleValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate one portable bundle and all embedded integrity evidence fail closed."""
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report_export_bundle(
        payload.bundle,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": (
            "Bundle validity proves deterministic packaging and receipt-chain integrity only. "
            "It does not infer causality or authorize any release transition."
        ),
    }


@router.post("/comparison/archive/integrity-report/export-bundle/download")
def download_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
    payload: IntelligenceComparisonArchiveIntegrityReportExportBundleValidationInput,
    current_user: User = Depends(get_current_user),
) -> Response:
    """Return canonical UTF-8 JSON bytes for one fully valid bounded bundle."""
    del current_user
    content = serialize_intelligence_comparison_archive_integrity_report_export_bundle(
        payload.bundle,
    )
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                'attachment; filename="comparison-archive-integrity-report-export-bundle.json"'
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )
