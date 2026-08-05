"""Deterministic receipts for validated internal-alpha intelligence comparisons."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison import validate_intelligence_comparison

_RECEIPT_SCHEMA = "lionsforge.internal-alpha-intelligence-comparison-receipt"
_RECEIPT_KEYS = {
    "schema",
    "schema_version",
    "comparison_sha256",
    "baseline_bundle_sha256",
    "candidate_bundle_sha256",
    "verification_state",
    "interpretation_notice",
    "receipt_sha256",
}
_NOTICE = (
    "This receipt proves deterministic comparison verification only and does not infer "
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


def _is_lower_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _receipt_body(comparison: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": _RECEIPT_SCHEMA,
        "schema_version": 1,
        "comparison_sha256": comparison["comparison_sha256"],
        "baseline_bundle_sha256": comparison["baseline_bundle_sha256"],
        "candidate_bundle_sha256": comparison["candidate_bundle_sha256"],
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_receipt(
    comparison: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Build a receipt only for an exactly validated comparison and bundle pair."""
    findings = validate_intelligence_comparison(comparison, baseline, candidate)
    if findings:
        raise ValueError("invalid comparison: " + "; ".join(findings))
    body = _receipt_body(comparison)
    return {
        **body,
        "receipt_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_receipt(
    receipt: dict[str, Any],
    comparison: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[str]:
    """Validate comparison integrity and exact receipt bindings fail closed."""
    findings = validate_intelligence_comparison(comparison, baseline, candidate)
    if not isinstance(receipt, dict):
        findings.append("comparison receipt must be an object")
        return sorted(set(findings))

    if set(receipt) != _RECEIPT_KEYS:
        findings.append("comparison receipt keys invalid")

    try:
        expected_body = _receipt_body(comparison)
    except (KeyError, TypeError, ValueError):
        findings.append("comparison receipt comparison binding invalid")
        return sorted(set(findings))

    if receipt.get("schema") != _RECEIPT_SCHEMA:
        findings.append("comparison receipt schema mismatch")
    schema_version = receipt.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        findings.append("comparison receipt schema version invalid")
    elif schema_version != 1:
        findings.append("comparison receipt schema version mismatch")

    for field in (
        "comparison_sha256",
        "baseline_bundle_sha256",
        "candidate_bundle_sha256",
    ):
        if not _is_lower_hex(receipt.get(field), 64):
            findings.append(f"comparison receipt {field} invalid")
        if receipt.get(field) != expected_body[field]:
            findings.append(f"comparison receipt {field} mismatch")

    for field in ("verification_state", "interpretation_notice"):
        if receipt.get(field) != expected_body[field]:
            findings.append(f"comparison receipt {field} mismatch")

    receipt_digest = receipt.get("receipt_sha256")
    if not _is_lower_hex(receipt_digest, 64):
        findings.append("comparison receipt digest invalid")
    expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    if receipt_digest != expected_digest:
        findings.append("comparison receipt digest mismatch")
    return sorted(set(findings))
