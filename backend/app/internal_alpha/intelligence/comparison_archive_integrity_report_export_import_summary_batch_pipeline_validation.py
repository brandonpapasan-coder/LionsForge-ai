"""Fail-closed validation for deterministic import-summary batch pipelines."""

from __future__ import annotations

from typing import Any

from .comparison_archive_integrity_report_export_import_summary_batch_pipeline import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline,
)

_EXPECTED_KEYS = {
    "batch_result",
    "diagnostics",
    "occurrence_projection",
    "interpretation_notice",
}


def validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
    summaries: list[dict[str, Any]],
    pipeline: dict[str, Any],
) -> list[str]:
    """Return deterministic findings for one submitted pipeline envelope."""
    if not isinstance(pipeline, dict):
        return ["pipeline must be a JSON object"]

    findings: list[str] = []
    if set(pipeline) != _EXPECTED_KEYS:
        findings.append("pipeline keys do not match the canonical shape")

    expected = build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        summaries
    )

    for key in ("batch_result", "diagnostics", "occurrence_projection"):
        if not isinstance(pipeline.get(key), dict):
            findings.append(f"{key} must be a JSON object")
        if pipeline.get(key) != expected[key]:
            findings.append(f"{key} does not match deterministic recomputation")

    if not isinstance(pipeline.get("interpretation_notice"), str):
        findings.append("interpretation_notice must be a string")
    if pipeline.get("interpretation_notice") != expected["interpretation_notice"]:
        findings.append(
            "interpretation_notice does not match deterministic recomputation"
        )

    return findings
