from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_pipeline import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline,
)
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline,
)
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response,
)
from app.models.user import User

router = APIRouter()

_VALIDATION_NOTICE = (
    "Pipeline validity proves deterministic recomputation of bounded "
    "transport-integrity artifacts only. It does not authorize any release transition."
)
_VALIDATION_RESPONSE_NOTICE = (
    "Pipeline validation-response verification proves deterministic recomputation "
    "of bounded transport-integrity results only. It does not authorize any release transition."
)


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineInput(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)
    summaries: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationInput(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)
    summaries: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    pipeline: dict[str, Any]


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationResponseInput(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)
    summaries: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    pipeline: dict[str, Any]
    response: dict[str, Any]


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)
    batch_result: dict[str, Any]
    diagnostics: dict[str, Any]
    occurrence_projection: dict[str, Any]
    interpretation_notice: str


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)
    valid: bool
    findings: list[str]
    interpretation_notice: str


@router.post(
    "/comparison/archive/integrity-report/export-bundle/import-summary/batch-pipeline",
    response_model=IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse,
)
def build_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineInput,
    current_user: User = Depends(get_current_user),
) -> IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse:
    del current_user
    pipeline = build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        payload.summaries
    )
    return IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse.model_validate(
        pipeline
    )


@router.post(
    "/comparison/archive/integrity-report/export-bundle/import-summary/batch-pipeline/validate",
    response_model=IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse,
)
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationInput,
    current_user: User = Depends(get_current_user),
) -> IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse:
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        payload.summaries,
        payload.pipeline,
    )
    return IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse(
        valid=not findings,
        findings=findings,
        interpretation_notice=_VALIDATION_NOTICE,
    )


@router.post(
    "/comparison/archive/integrity-report/export-bundle/import-summary/batch-pipeline/validate-response",
    response_model=IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse,
)
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationResponseInput,
    current_user: User = Depends(get_current_user),
) -> IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse:
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
        payload.summaries,
        payload.pipeline,
        payload.response,
    )
    return IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse(
        valid=not findings,
        findings=findings,
        interpretation_notice=_VALIDATION_RESPONSE_NOTICE,
    )
