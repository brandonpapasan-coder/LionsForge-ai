from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_pipeline import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline,
)
from app.models.user import User

router = APIRouter()


class IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineInput(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)
    summaries: list[dict[str, Any]] = Field(min_length=1, max_length=100)


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
