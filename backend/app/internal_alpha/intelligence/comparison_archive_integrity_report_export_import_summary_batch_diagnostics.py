"""Deterministic diagnostics for validated import-summary batch results."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .comparison_archive_integrity_report_export_import_summary_batch_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result,
)

_NOTICE = (
    "Batch diagnostics summarize validated transport-integrity findings only. "
    "They do not authorize any release transition."
)


def build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
    summaries: list[dict[str, Any]],
    batch_result: dict[str, Any],
) -> dict[str, Any]:
    """Return stable invalid indexes and finding frequencies for one valid batch result."""
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result(
        summaries,
        batch_result,
    )
    if findings:
        raise ValueError(
            "invalid integrity report export import summary batch result: "
            + "; ".join(findings)
        )

    invalid_indexes: list[int] = []
    finding_counts: Counter[str] = Counter()
    for result in batch_result["results"]:
        if not result["valid"]:
            invalid_indexes.append(result["index"])
        finding_counts.update(result["findings"])

    frequencies = [
        {"finding": finding, "count": finding_counts[finding]}
        for finding in sorted(finding_counts)
    ]
    return {
        "summary_count": batch_result["summary_count"],
        "invalid_summary_count": len(invalid_indexes),
        "invalid_indexes": invalid_indexes,
        "distinct_finding_count": len(frequencies),
        "finding_count": sum(item["count"] for item in frequencies),
        "finding_frequencies": frequencies,
        "interpretation_notice": _NOTICE,
    }
