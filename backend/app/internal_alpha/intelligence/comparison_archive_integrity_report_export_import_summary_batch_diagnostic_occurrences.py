"""Deterministic occurrence projection for validated batch diagnostics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .comparison_archive_integrity_report_export_import_summary_batch_diagnostics_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics,
)

_NOTICE = (
    "Diagnostic occurrences locate validated transport-integrity findings only. "
    "They do not authorize any release transition."
)


def build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
    summaries: list[dict[str, Any]],
    batch_result: dict[str, Any],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Return stable finding-to-summary-index occurrences for valid diagnostics."""
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
        summaries,
        batch_result,
        diagnostics,
    )
    if findings:
        raise ValueError(
            "invalid integrity report export import summary batch diagnostics: "
            + "; ".join(findings)
        )

    indexes_by_finding: defaultdict[str, set[int]] = defaultdict(set)
    for result in batch_result["results"]:
        for finding in result["findings"]:
            indexes_by_finding[finding].add(result["index"])

    frequency_by_finding = {
        item["finding"]: item["count"] for item in diagnostics["finding_frequencies"]
    }
    occurrences = [
        {
            "finding": finding,
            "occurrence_count": frequency_by_finding[finding],
            "affected_summary_count": len(indexes_by_finding[finding]),
            "summary_indexes": sorted(indexes_by_finding[finding]),
        }
        for finding in sorted(frequency_by_finding)
    ]
    return {
        "summary_count": diagnostics["summary_count"],
        "finding_count": diagnostics["finding_count"],
        "distinct_finding_count": diagnostics["distinct_finding_count"],
        "occurrences": occurrences,
        "interpretation_notice": _NOTICE,
    }
