"""Deterministic receipts for validated internal-alpha intelligence comparisons."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison import validate_intelligence_comparison

_RECEIPT_SCHEMA = "lionsforge.internal-alpha-intelligence-comparison-receipt"
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
    expected_body = _receipt_body(comparison)

    if receipt.get("schema") != _RECEIPT_SCHEMA:
        findings.append("comparison receipt schema mismatch")
    if receipt.get("schema_version") != 1:
        findings.append("comparison receipt schema version mismatch")
    for field in (
        "comparison_sha256",
        "baseline_bundle_sha256",
        "candidate_bundle_sha256",
        "verification_state",
        "interpretation_notice",
    ):
        if receipt.get(field) != expected_body[field]:
            findings.append(f"comparison receipt {field} mismatch")
    expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    if receipt.get("receipt_sha256") != expected_digest:
        findings.append("comparison receipt digest mismatch")
    return findings
