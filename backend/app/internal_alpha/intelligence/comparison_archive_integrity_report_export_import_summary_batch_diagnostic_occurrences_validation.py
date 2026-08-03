"""Fail-closed validation for deterministic diagnostic occurrence projections."""

from __future__ import annotations

from typing import Any

from .comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences,
)

_EXPECTED_KEYS = {
    "summary_count",
    "finding_count",
    "distinct_finding_count",
    "occurrences",
    "interpretation_notice",
}
_EXPECTED_OCCURRENCE_KEYS = {
    "finding",
    "occurrence_count",
    "affected_summary_count",
    "summary_indexes",
}


def validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
    summaries: list[dict[str, Any]],
    batch_result: dict[str, Any],
    diagnostics: dict[str, Any],
    occurrence_projection: dict[str, Any],
) -> list[str]:
    """Return deterministic findings for one submitted occurrence projection."""
    findings: list[str] = []
    if not isinstance(occurrence_projection, dict):
        return ["occurrence projection must be a JSON object"]
    if set(occurrence_projection) != _EXPECTED_KEYS:
        findings.append("occurrence projection keys do not match the canonical shape")

    try:
        expected = build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
            summaries,
            batch_result,
            diagnostics,
        )
    except ValueError as exc:
        return [str(exc)]

    occurrences = occurrence_projection.get("occurrences")
    if not isinstance(occurrences, list):
        findings.append("occurrences must be a list")
    else:
        for index, item in enumerate(occurrences):
            if not isinstance(item, dict):
                findings.append(f"occurrences[{index}] must be a JSON object")
                continue
            if set(item) != _EXPECTED_OCCURRENCE_KEYS:
                findings.append(
                    f"occurrences[{index}] keys do not match the canonical shape"
                )

    for key in (
        "summary_count",
        "finding_count",
        "distinct_finding_count",
        "occurrences",
        "interpretation_notice",
    ):
        if occurrence_projection.get(key) != expected[key]:
            findings.append(f"{key} does not match deterministic recomputation")

    return findings
