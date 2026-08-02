"""Bounded deterministic batch validation for integrity-report import summaries."""

from __future__ import annotations

from typing import Any

from .comparison_archive_integrity_report_export_import_summary import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary,
)

_MAX_SUMMARIES = 100
_BATCH_NOTICE = (
    "Batch validation reports deterministic transport-integrity findings only. "
    "It does not authorize any release transition."
)


def validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate at most 100 summaries and preserve exact input ordering in results."""
    if not isinstance(summaries, list):
        raise TypeError("integrity report export import summary batch must be a list")
    if not summaries:
        raise ValueError("integrity report export import summary batch must not be empty")
    if len(summaries) > _MAX_SUMMARIES:
        raise ValueError("integrity report export import summary batch exceeds item limit")

    results: list[dict[str, Any]] = []
    valid_count = 0
    finding_count = 0
    for index, summary in enumerate(summaries):
        findings = (
            validate_intelligence_comparison_archive_integrity_report_export_import_summary(
                summary
            )
            if isinstance(summary, dict)
            else ["integrity report export import summary must be an object"]
        )
        valid = not findings
        if valid:
            valid_count += 1
        finding_count += len(findings)
        results.append(
            {
                "index": index,
                "valid": valid,
                "findings": findings,
            }
        )

    return {
        "summary_count": len(summaries),
        "valid_count": valid_count,
        "invalid_count": len(summaries) - valid_count,
        "finding_count": finding_count,
        "results": results,
        "interpretation_notice": _BATCH_NOTICE,
    }
