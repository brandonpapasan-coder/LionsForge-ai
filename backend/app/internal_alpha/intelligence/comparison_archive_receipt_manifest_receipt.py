"""Deterministic receipts for validated comparison archive receipt manifests."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .comparison_archive_receipt_manifest import (
    validate_intelligence_comparison_archive_receipt_manifest,
)

_RECEIPT_SCHEMA = (
    "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-receipt"
)
_RECEIPT_KEYS = {
    "schema",
    "schema_version",
    "manifest_sha256",
    "entry_count",
    "verification_state",
    "interpretation_notice",
    "receipt_sha256",
}
_NOTICE = (
    "This receipt proves deterministic archive receipt manifest verification only and does not "
    "infer causality or authorize any release transition."
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _receipt_body(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": _RECEIPT_SCHEMA,
        "schema_version": 1,
        "manifest_sha256": manifest["manifest_sha256"],
        "entry_count": manifest["entry_count"],
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def build_intelligence_comparison_archive_receipt_manifest_receipt(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Issue a compact receipt only for a fully valid archive receipt manifest."""
    findings = validate_intelligence_comparison_archive_receipt_manifest(manifest)
    if findings:
        raise ValueError("invalid comparison archive receipt manifest: " + "; ".join(findings))
    body = _receipt_body(manifest)
    return {
        **body,
        "receipt_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt_manifest_receipt(
    receipt: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    """Validate manifest integrity and the receipt's exact manifest binding fail closed."""
    findings = validate_intelligence_comparison_archive_receipt_manifest(manifest)
    if not isinstance(receipt, dict):
        findings.append("comparison archive receipt manifest receipt must be an object")
        return findings

    if set(receipt) != _RECEIPT_KEYS:
        findings.append("comparison archive receipt manifest receipt keys invalid")

    try:
        expected_body = _receipt_body(manifest)
    except (KeyError, TypeError, ValueError):
        findings.append("comparison archive receipt manifest receipt binding invalid")
        return findings

    if receipt.get("schema") != _RECEIPT_SCHEMA:
        findings.append("comparison archive receipt manifest receipt schema mismatch")
    if type(receipt.get("schema_version")) is not int or receipt.get("schema_version") != 1:
        findings.append("comparison archive receipt manifest receipt schema version mismatch")
    if type(receipt.get("entry_count")) is not int:
        findings.append("comparison archive receipt manifest receipt entry_count invalid")
    elif receipt.get("entry_count") != expected_body["entry_count"]:
        findings.append("comparison archive receipt manifest receipt entry_count mismatch")

    manifest_digest = receipt.get("manifest_sha256")
    if not _is_sha256(manifest_digest):
        findings.append("comparison archive receipt manifest receipt manifest_sha256 invalid")
    elif manifest_digest != expected_body["manifest_sha256"]:
        findings.append("comparison archive receipt manifest receipt manifest_sha256 mismatch")

    for field in ("verification_state", "interpretation_notice"):
        if receipt.get(field) != expected_body[field]:
            findings.append(f"comparison archive receipt manifest receipt {field} mismatch")

    receipt_digest = receipt.get("receipt_sha256")
    if not _is_sha256(receipt_digest):
        findings.append("comparison archive receipt manifest receipt digest invalid")
    else:
        expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
        if receipt_digest != expected_digest:
            findings.append("comparison archive receipt manifest receipt digest mismatch")
    return findings
