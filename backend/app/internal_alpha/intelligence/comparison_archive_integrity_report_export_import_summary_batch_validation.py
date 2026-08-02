"""Fail-closed validation for deterministic import-summary batch results."""

from __future__ import annotations

from typing import Any

from .comparison_archive_integrity_report_export_import_summary_batch import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch,
)

_BATCH_RESULT_KEYS = {
    "summary_count",
    "valid_count",
    "invalid_count",
    "finding_count",
    "results",
    "interpretation_notice",
}
_RESULT_KEYS = {"index", "valid", "findings"}


def validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result(
    summaries: list[dict[str, Any]],
    batch_result: dict[str, Any],
) -> list[str]:
    """Recompute one bounded batch result and compare its exact deterministic fields."""
    findings: list[str] = []
    if not isinstance(batch_result, dict):
        return ["integrity report export import summary batch result must be an object"]
    if set(batch_result) != _BATCH_RESULT_KEYS:
        findings.append("integrity report export import summary batch result keys invalid")

    try:
        expected = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(
            summaries
        )
    except (TypeError, ValueError) as exc:
        return [f"integrity report export import summary batch source invalid: {exc}"]

    for field in (
        "summary_count",
        "valid_count",
        "invalid_count",
        "finding_count",
        "interpretation_notice",
    ):
        if batch_result.get(field) != expected[field]:
            findings.append(
                f"integrity report export import summary batch result {field} mismatch"
            )

    submitted_results = batch_result.get("results")
    if not isinstance(submitted_results, list):
        findings.append("integrity report export import summary batch result results must be a list")
        return findings
    if len(submitted_results) != len(expected["results"]):
        findings.append("integrity report export import summary batch result results length mismatch")
        return findings

    for index, (submitted, expected_result) in enumerate(
        zip(submitted_results, expected["results"], strict=True)
    ):
        if not isinstance(submitted, dict):
            findings.append(
                f"integrity report export import summary batch result item {index} must be an object"
            )
            continue
        if set(submitted) != _RESULT_KEYS:
            findings.append(
                f"integrity report export import summary batch result item {index} keys invalid"
            )
        for field in ("index", "valid", "findings"):
            if submitted.get(field) != expected_result[field]:
                findings.append(
                    f"integrity report export import summary batch result item {index} {field} mismatch"
                )

    return findings
