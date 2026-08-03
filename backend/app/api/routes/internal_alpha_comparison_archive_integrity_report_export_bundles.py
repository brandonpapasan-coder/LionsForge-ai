from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_bundle import (
    build_intelligence_comparison_archive_integrity_report_export_bundle,
    serialize_intelligence_comparison_archive_integrity_report_export_bundle,
    summarize_intelligence_comparison_archive_integrity_report_export_import,
    validate_intelligence_comparison_archive_integrity_report_export_bundle,
)
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary,
)
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch,
)
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostics import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics,
)
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostics_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics,
)
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result,
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


class IntelligenceComparisonArchiveIntegrityReportExportBundleImportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    content: str = Field(min_length=1, max_length=1_000_000)


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: dict[str, Any]


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summaries: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchResultValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summaries: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    batch_result: dict[str, Any]


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticsValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summaries: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    batch_result: dict[str, Any]
    diagnostics: dict[str, Any]


@router.post("/comparison/archive/integrity-report/export-bundle")
def create_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
    payload: IntelligenceComparisonArchiveIntegrityReportExportBundleInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return build_intelligence_comparison_archive_integrity_report_export_bundle(
        payload.report, payload.receipt, payload.manifest
    )


@router.post("/comparison/archive/integrity-report/export-bundle/validate")
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
    payload: IntelligenceComparisonArchiveIntegrityReportExportBundleValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report_export_bundle(payload.bundle)
    return {"valid": not findings, "findings": findings, "interpretation_notice": "Bundle validity proves deterministic packaging and receipt-chain integrity only. It does not infer causality or authorize any release transition."}


@router.post("/comparison/archive/integrity-report/export-bundle/download")
def download_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
    payload: IntelligenceComparisonArchiveIntegrityReportExportBundleValidationInput,
    current_user: User = Depends(get_current_user),
) -> Response:
    del current_user
    content = serialize_intelligence_comparison_archive_integrity_report_export_bundle(payload.bundle)
    return Response(content=content, media_type="application/json", headers={"Content-Disposition": 'attachment; filename="comparison-archive-integrity-report-export-bundle.json"', "X-Content-Type-Options": "nosniff"})


@router.post("/comparison/archive/integrity-report/export-bundle/import")
def import_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
    payload: IntelligenceComparisonArchiveIntegrityReportExportBundleImportInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    try:
        return summarize_intelligence_comparison_archive_integrity_report_export_import(payload.content.encode("utf-8"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/comparison/archive/integrity-report/export-bundle/import-summary/validate")
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary(payload.summary)
    return {"valid": not findings, "findings": findings, "interpretation_notice": "Summary validity proves reconstructed canonical transport metadata only. It does not infer causality or authorize any release transition."}


@router.post("/comparison/archive/integrity-report/export-bundle/import-summary/validate-batch")
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(payload.summaries)


@router.post("/comparison/archive/integrity-report/export-bundle/import-summary/validate-batch-result")
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchResultValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result(
        payload.summaries, payload.batch_result
    )
    return {"valid": not findings, "findings": findings, "interpretation_notice": "Batch-result validity proves deterministic recomputation of bounded transport-integrity findings only. It does not authorize any release transition."}


@router.post("/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics")
def build_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchResultValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    try:
        return build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
            payload.summaries, payload.batch_result
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/validate")
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticsValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
        payload.summaries, payload.batch_result, payload.diagnostics
    )
    return {"valid": not findings, "findings": findings, "interpretation_notice": "Diagnostics validity proves deterministic recomputation of bounded transport-integrity diagnostics only. It does not authorize any release transition."}
