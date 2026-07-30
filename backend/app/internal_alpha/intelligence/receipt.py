"""Deterministic integrity receipts for internal-alpha intelligence reports."""

from __future__ import annotations

import hashlib
import json
from typing import Any

_REPORT_SCHEMA = "lionsforge.internal-alpha-intelligence-report"
_RECEIPT_SCHEMA = "lionsforge.internal-alpha-intelligence-receipt"


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def build_intelligence_receipt(report: dict[str, Any]) -> dict[str, Any]:
    """Bind one bounded report to a deterministic SHA-256 receipt."""
    if report.get("schema") != _REPORT_SCHEMA or report.get("schema_version") != 1:
        raise ValueError("unsupported intelligence report schema")
    candidate_sha = report.get("candidate_sha")
    if not isinstance(candidate_sha, str) or len(candidate_sha) != 40:
        raise ValueError("report candidate_sha is invalid")

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
