"""Deterministic composition of import-summary batch integrity artifacts."""

from __future__ import annotations

from typing import Any

from .comparison_archive_integrity_report_export_import_summary_batch import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch,
)
from .comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences,
)
from .comparison_archive_integrity_report_export_import_summary_batch_diagnostics import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics,
)

_NOTICE = (
    "The batch pipeline composes bounded deterministic transport-integrity "
    "artifacts only. It does not authorize any release transition."
)


def build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the canonical batch result, diagnostics, and occurrence projection."""
    batch_result = (
        validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(
            summaries
        )
    )
    diagnostics = build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
        summaries,
        batch_result,
    )
    occurrence_projection = build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
        summaries,
        batch_result,
        diagnostics,
    )
    return {
        "batch_result": batch_result,
        "diagnostics": diagnostics,
        "occurrence_projection": occurrence_projection,
        "interpretation_notice": _NOTICE,
    }
