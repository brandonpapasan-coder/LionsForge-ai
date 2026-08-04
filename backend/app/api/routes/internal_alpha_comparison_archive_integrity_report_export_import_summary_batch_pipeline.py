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


@router.post(
    "/comparison/archive/integrity-report/export-bundle/import-summary/batch-pipeline"
)
def build_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        payload.summaries
    )


@router.post(
    "/comparison/archive/integrity-report/export-bundle/import-summary/batch-pipeline/validate"
)
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        payload.summaries,
        payload.pipeline,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": _VALIDATION_NOTICE,
    }


@router.post(
    "/comparison/archive/integrity-report/export-bundle/import-summary/batch-pipeline/validate-response"
)
def validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
    payload: IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationResponseInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
        payload.summaries,
        payload.pipeline,
        payload.response,
    )
    return {
        "valid": not findings,
        "findings": findings,
        "interpretation_notice": _VALIDATION_RESPONSE_NOTICE,
    }
