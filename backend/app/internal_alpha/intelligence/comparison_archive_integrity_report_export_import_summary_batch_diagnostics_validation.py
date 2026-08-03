"""Fail-closed validation for deterministic import-summary batch diagnostics."""

from __future__ import annotations

from typing import Any

from .comparison_archive_integrity_report_export_import_summary_batch_diagnostics import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics,
)

_DIAGNOSTICS_KEYS = {
    "summary_count",
    "invalid_summary_count",
    "invalid_indexes",
    "distinct_finding_count",
    "finding_count",
    "finding_frequencies",
    "interpretation_notice",
}
_FREQUENCY_KEYS = {"finding", "count"}


def validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
    summaries: list[dict[str, Any]],
    batch_result: dict[str, Any],
    diagnostics: dict[str, Any],
) -> list[str]:
    """Recompute one diagnostics projection and compare its exact deterministic fields."""
    findings: list[str] = []
    if not isinstance(diagnostics, dict):
        return ["integrity report export import summary batch diagnostics must be an object"]
    if set(diagnostics) != _DIAGNOSTICS_KEYS:
        findings.append("integrity report export import summary batch diagnostics keys invalid")

    try:
        expected = build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
            summaries,
            batch_result,
        )
    except (TypeError, ValueError) as exc:
        return [f"integrity report export import summary batch diagnostics source invalid: {exc}"]

    for field in (
        "summary_count",
        "invalid_summary_count",
        "invalid_indexes",
        "distinct_finding_count",
        "finding_count",
        "interpretation_notice",
    ):
        if diagnostics.get(field) != expected[field]:
            findings.append(
                f"integrity report export import summary batch diagnostics {field} mismatch"
            )

    submitted_frequencies = diagnostics.get("finding_frequencies")
    if not isinstance(submitted_frequencies, list):
        findings.append(
            "integrity report export import summary batch diagnostics finding_frequencies must be a list"
        )
        return findings
    if len(submitted_frequencies) != len(expected["finding_frequencies"]):
        findings.append(
            "integrity report export import summary batch diagnostics finding_frequencies length mismatch"
        )
        return findings

    for index, (submitted, expected_frequency) in enumerate(
        zip(submitted_frequencies, expected["finding_frequencies"], strict=True)
    ):
        if not isinstance(submitted, dict):
            findings.append(
                f"integrity report export import summary batch diagnostics frequency {index} must be an object"
            )
            continue
        if set(submitted) != _FREQUENCY_KEYS:
            findings.append(
                f"integrity report export import summary batch diagnostics frequency {index} keys invalid"
            )
        for field in ("finding", "count"):
            if submitted.get(field) != expected_frequency[field]:
                findings.append(
                    f"integrity report export import summary batch diagnostics frequency {index} {field} mismatch"
                )

    return findings
