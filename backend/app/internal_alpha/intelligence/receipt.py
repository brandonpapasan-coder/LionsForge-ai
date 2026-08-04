"""Deterministic integrity receipts for internal-alpha intelligence reports."""

from __future__ import annotations

import hashlib
import json
from typing import Any

_REPORT_SCHEMA = "lionsforge.internal-alpha-intelligence-report"
_RECEIPT_SCHEMA = "lionsforge.internal-alpha-intelligence-receipt"
_REPORT_KEYS = {
    "schema",
    "schema_version",
    "candidate_sha",
    "metrics",
    "readiness",
    "repeated_categories",
    "blocking_reasons",
    "interpretation_notice",
}
_RECEIPT_KEYS = {
    "schema",
    "schema_version",
    "candidate_sha",
    "report_sha256",
}


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _is_sha(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _report_shape_is_valid(report: object) -> bool:
    if not isinstance(report, dict) or set(report) != _REPORT_KEYS:
        return False
    if report.get("schema") != _REPORT_SCHEMA or report.get("schema_version") != 1:
        return False
    if not _is_sha(report.get("candidate_sha"), 40):
        return False
    if not isinstance(report.get("metrics"), dict):
        return False
    if not isinstance(report.get("readiness"), dict):
        return False
    if not isinstance(report.get("repeated_categories"), list):
        return False
    if not isinstance(report.get("blocking_reasons"), list):
        return False
    if not isinstance(report.get("interpretation_notice"), str):
        return False
    return True


def _receipt_shape_is_valid(receipt: object) -> bool:
    if not isinstance(receipt, dict) or set(receipt) != _RECEIPT_KEYS:
        return False
    if receipt.get("schema") != _RECEIPT_SCHEMA or receipt.get("schema_version") != 1:
        return False
    if not _is_sha(receipt.get("candidate_sha"), 40):
        return False
    if not _is_sha(receipt.get("report_sha256"), 64):
        return False
    return True


def build_intelligence_receipt(report: dict[str, Any]) -> dict[str, Any]:
    """Bind one bounded report to a deterministic SHA-256 receipt."""
    if report.get("schema") != _REPORT_SCHEMA or report.get("schema_version") != 1:
        raise ValueError("unsupported intelligence report schema")
    if not _report_shape_is_valid(report):
        raise ValueError("invalid intelligence report shape")

    candidate_sha = report["candidate_sha"]
    digest = hashlib.sha256(_canonical_bytes(report)).hexdigest()
    return {
        "schema": _RECEIPT_SCHEMA,
        "schema_version": 1,
        "candidate_sha": candidate_sha,
        "report_sha256": digest,
    }


def validate_intelligence_receipt(
    receipt: dict[str, Any], report: dict[str, Any]
) -> list[str]:
    """Return deterministic fail-closed findings for receipt substitution or drift."""
    findings: list[str] = []
    if receipt.get("schema") != _RECEIPT_SCHEMA:
        findings.append("unsupported receipt schema")
    if receipt.get("schema_version") != 1:
        findings.append("unsupported receipt schema version")
    if not _receipt_shape_is_valid(receipt):
        findings.append("invalid intelligence receipt")
    if receipt.get("candidate_sha") != report.get("candidate_sha"):
        findings.append("candidate SHA mismatch")

    try:
        expected = build_intelligence_receipt(report)
    except (TypeError, ValueError):
        findings.append("invalid intelligence report")
        return sorted(set(findings))

    if receipt.get("report_sha256") != expected["report_sha256"]:
        findings.append("report digest mismatch")
    return sorted(set(findings))
