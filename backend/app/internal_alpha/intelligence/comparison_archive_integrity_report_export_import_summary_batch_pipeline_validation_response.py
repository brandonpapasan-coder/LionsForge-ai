"""Fail-closed validation for batch-pipeline validation API responses."""

from __future__ import annotations

from typing import Any

from .comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline,
)

_EXPECTED_KEYS = {"valid", "findings", "interpretation_notice"}
_NOTICE = (
    "Pipeline validity proves deterministic recomputation of bounded "
    "transport-integrity artifacts only. It does not authorize any release transition."
)


def validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
    summaries: list[dict[str, Any]],
    pipeline: dict[str, Any],
    response: dict[str, Any],
) -> list[str]:
    """Return deterministic findings for one submitted pipeline-validation response."""
    if not isinstance(response, dict):
        return ["validation response must be a JSON object"]

    findings: list[str] = []
    if set(response) != _EXPECTED_KEYS:
        findings.append("validation response keys do not match the canonical shape")

    expected_findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        summaries,
        pipeline,
    )
    expected = {
        "valid": not expected_findings,
        "findings": expected_findings,
        "interpretation_notice": _NOTICE,
    }

    if not isinstance(response.get("valid"), bool):
        findings.append("valid must be a boolean")
    if not isinstance(response.get("findings"), list):
        findings.append("findings must be a list")
    elif any(not isinstance(item, str) for item in response["findings"]):
        findings.append("findings must contain only strings")
    if not isinstance(response.get("interpretation_notice"), str):
        findings.append("interpretation_notice must be a string")

    for key in ("valid", "findings", "interpretation_notice"):
        if response.get(key) != expected[key]:
            findings.append(f"{key} does not match deterministic recomputation")

    return findings
