"""Deterministic receipts for validated archive bundle-receipt ledgers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison_archive_receipt_manifest_bundle_receipt_ledger import (
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger,
)

_RECEIPT_SCHEMA = (
    "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-"
    "bundle-receipt-ledger-receipt"
)
_RECEIPT_KEYS = {
    "schema",
    "schema_version",
    "ledger_sha256",
    "entry_count",
    "verification_state",
    "interpretation_notice",
    "ledger_receipt_sha256",
}
_NOTICE = (
    "This receipt proves deterministic archive bundle-receipt ledger verification only and "
    "does not infer causality or authorize any release transition."
)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _receipt_body(ledger: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": _RECEIPT_SCHEMA,
        "schema_version": 1,
        "ledger_sha256": ledger["ledger_sha256"],
        "entry_count": ledger["entry_count"],
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
    ledger: dict[str, Any],
) -> dict[str, Any]:
    """Issue one compact receipt only for a fully valid bundle-receipt ledger."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        ledger
    )
    if findings:
        raise ValueError("invalid comparison archive bundle receipt ledger: " + "; ".join(findings))
    body = _receipt_body(ledger)
    return {
        **body,
        "ledger_receipt_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
    receipt: dict[str, Any],
    ledger: dict[str, Any],
) -> list[str]:
    """Validate ledger integrity and the receipt's exact ledger binding fail closed."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        ledger
    )
    if not isinstance(receipt, dict):
        findings.append("comparison archive bundle receipt ledger receipt must be an object")
        return findings

    if set(receipt) != _RECEIPT_KEYS:
        findings.append("comparison archive bundle receipt ledger receipt keys invalid")

    try:
        expected_body = _receipt_body(ledger)
    except (KeyError, TypeError, ValueError):
        findings.append("comparison archive bundle receipt ledger receipt binding invalid")
        return findings

    if receipt.get("schema") != _RECEIPT_SCHEMA:
        findings.append("comparison archive bundle receipt ledger receipt schema mismatch")
    if receipt.get("schema_version") != 1:
        findings.append("comparison archive bundle receipt ledger receipt schema version mismatch")
    for field in (
        "ledger_sha256",
        "entry_count",
        "verification_state",
        "interpretation_notice",
    ):
        if receipt.get(field) != expected_body[field]:
            findings.append(f"comparison archive bundle receipt ledger receipt {field} mismatch")

    expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    if receipt.get("ledger_receipt_sha256") != expected_digest:
        findings.append("comparison archive bundle receipt ledger receipt digest mismatch")
    return findings
