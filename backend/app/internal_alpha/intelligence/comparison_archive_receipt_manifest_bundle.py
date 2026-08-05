"""Deterministic transport bundles for archive receipt manifests and receipts."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .comparison_archive_receipt_manifest_receipt import (
    validate_intelligence_comparison_archive_receipt_manifest_receipt,
)

_BUNDLE_SCHEMA = (
    "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-bundle"
)
_BUNDLE_KEYS = {
    "schema",
    "schema_version",
    "manifest",
    "receipt",
    "manifest_sha256",
    "receipt_sha256",
    "entry_count",
    "bundle_sha256",
    "interpretation_notice",
}
_NOTICE = (
    "This bundle preserves deterministic archive receipt manifest transfer integrity only and "
    "does not infer causality or authorize any release transition."
)
_CANONICAL_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _is_canonical_sha256(value: object) -> bool:
    return isinstance(value, str) and _CANONICAL_SHA256_RE.fullmatch(value) is not None


def _bundle_body(
    manifest: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": _BUNDLE_SCHEMA,
        "schema_version": 1,
        "manifest": manifest,
        "receipt": receipt,
        "manifest_sha256": manifest["manifest_sha256"],
        "receipt_sha256": receipt["receipt_sha256"],
        "entry_count": manifest["entry_count"],
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_receipt_manifest_bundle(
    manifest: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Build one bundle only from a valid manifest and its exact valid receipt."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_receipt(
        receipt,
        manifest,
    )
    if findings:
        raise ValueError("invalid comparison archive receipt manifest chain: " + "; ".join(findings))
    body = _bundle_body(manifest, receipt)
    return {
        **body,
        "bundle_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt_manifest_bundle(
    bundle: dict[str, Any],
) -> list[str]:
    """Validate the complete manifest bundle and all exact bindings fail closed."""
    if not isinstance(bundle, dict):
        return ["comparison archive receipt manifest bundle must be an object"]

    findings: list[str] = []
    if set(bundle) != _BUNDLE_KEYS:
        findings.append("comparison archive receipt manifest bundle keys invalid")

    manifest = bundle.get("manifest")
    receipt = bundle.get("receipt")
    if not isinstance(manifest, dict) or not isinstance(receipt, dict):
        findings.append("comparison archive receipt manifest bundle chain invalid")
        return findings

    findings.extend(
        validate_intelligence_comparison_archive_receipt_manifest_receipt(
            receipt,
            manifest,
        )
    )

    try:
        expected_body = _bundle_body(manifest, receipt)
    except (KeyError, TypeError, ValueError):
        findings.append("comparison archive receipt manifest bundle binding invalid")
        return findings

    if bundle.get("schema") != _BUNDLE_SCHEMA:
        findings.append("comparison archive receipt manifest bundle schema mismatch")

    schema_version = bundle.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        findings.append("comparison archive receipt manifest bundle schema version mismatch")

    entry_count = bundle.get("entry_count")
    if type(entry_count) is not int or entry_count != expected_body["entry_count"]:
        findings.append("comparison archive receipt manifest bundle entry_count mismatch")

    for field in ("manifest_sha256", "receipt_sha256"):
        value = bundle.get(field)
        if not _is_canonical_sha256(value):
            findings.append(f"comparison archive receipt manifest bundle {field} invalid")
        elif value != expected_body[field]:
            findings.append(f"comparison archive receipt manifest bundle {field} mismatch")

    if bundle.get("interpretation_notice") != expected_body["interpretation_notice"]:
        findings.append("comparison archive receipt manifest bundle interpretation_notice mismatch")

    expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    bundle_digest = bundle.get("bundle_sha256")
    if not _is_canonical_sha256(bundle_digest):
        findings.append("comparison archive receipt manifest bundle digest invalid")
    elif bundle_digest != expected_digest:
        findings.append("comparison archive receipt manifest bundle digest mismatch")
    return findings
