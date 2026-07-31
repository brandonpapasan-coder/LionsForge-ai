"""Deterministic receipts for validated comparison archives."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison_archive import validate_intelligence_comparison_archive

_RECEIPT_SCHEMA = "lionsforge.internal-alpha-intelligence-comparison-archive-receipt"
_RECEIPT_KEYS = {
    "schema",
    "schema_version",
    "archive_sha256",
    "verification_state",
    "interpretation_notice",
    "receipt_sha256",
}
_NOTICE = (
    "This receipt proves deterministic comparison archive verification only and does not infer "
    "causality or authorize any release transition."
)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _receipt_body(archive: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": _RECEIPT_SCHEMA,
        "schema_version": 1,
        "archive_sha256": archive["archive_sha256"],
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_receipt(
    archive: dict[str, Any],
) -> dict[str, Any]:
    """Issue a compact receipt only for a fully valid comparison archive."""
    findings = validate_intelligence_comparison_archive(archive)
    if findings:
        raise ValueError("invalid comparison archive: " + "; ".join(findings))
    body = _receipt_body(archive)
    return {
        **body,
        "receipt_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt(
    receipt: dict[str, Any],
    archive: dict[str, Any],
) -> list[str]:
    """Validate archive integrity and the receipt's exact archive binding fail closed."""
    findings = validate_intelligence_comparison_archive(archive)
    if not isinstance(receipt, dict):
        findings.append("comparison archive receipt must be an object")
        return findings

    if set(receipt) != _RECEIPT_KEYS:
        findings.append("comparison archive receipt keys invalid")

    try:
        expected_body = _receipt_body(archive)
    except (KeyError, TypeError, ValueError):
        findings.append("comparison archive receipt archive binding invalid")
        return findings

    if receipt.get("schema") != _RECEIPT_SCHEMA:
        findings.append("comparison archive receipt schema mismatch")
    if receipt.get("schema_version") != 1:
        findings.append("comparison archive receipt schema version mismatch")
    for field in (
        "archive_sha256",
        "verification_state",
        "interpretation_notice",
    ):
        if receipt.get(field) != expected_body[field]:
            findings.append(f"comparison archive receipt {field} mismatch")

    expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    if receipt.get("receipt_sha256") != expected_digest:
        findings.append("comparison archive receipt digest mismatch")
    return findings
