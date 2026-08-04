"""Bounded deterministic bundles for internal-alpha intelligence receipts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .receipt import validate_intelligence_receipt

_BUNDLE_SCHEMA = "lionsforge.internal-alpha-intelligence-bundle"
_BUNDLE_KEYS = {
    "schema",
    "schema_version",
    "entry_count",
    "entries",
    "bundle_sha256",
}
_MAX_ENTRIES = 100


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
        and all(character in "0123456789abcdef" for character in value)
    )


def build_intelligence_bundle(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one deterministic bundle from validated report and receipt pairs."""
    if not 1 <= len(entries) <= _MAX_ENTRIES:
        raise ValueError("bundle requires between 1 and 100 entries")

    normalized: list[dict[str, Any]] = []
    candidates: set[str] = set()
    for entry in entries:
        if set(entry) != {"report", "receipt"}:
            raise ValueError("bundle entries must contain only report and receipt")
        report = entry["report"]
        receipt = entry["receipt"]
        if not isinstance(report, dict) or not isinstance(receipt, dict):
            raise TypeError("bundle report and receipt must be objects")
        findings = validate_intelligence_receipt(receipt, report)
        if findings:
            raise ValueError("invalid bundle entry: " + "; ".join(findings))
        candidate_sha = report.get("candidate_sha")
        if candidate_sha in candidates:
            raise ValueError("bundle candidate SHAs must be unique")
        candidates.add(candidate_sha)
        normalized.append({"report": report, "receipt": receipt})

    normalized.sort(key=lambda item: item["report"]["candidate_sha"])
    body = {
        "schema": _BUNDLE_SCHEMA,
        "schema_version": 1,
        "entry_count": len(normalized),
        "entries": normalized,
    }
    return {**body, "bundle_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest()}


def validate_intelligence_bundle(bundle: dict[str, Any]) -> list[str]:
    """Return deterministic findings for malformed, substituted, or drifted bundles."""
    findings: list[str] = []
    if set(bundle) != _BUNDLE_KEYS:
        findings.append("bundle fields are invalid")
    if bundle.get("schema") != _BUNDLE_SCHEMA:
        findings.append("unsupported bundle schema")
    if type(bundle.get("schema_version")) is not int or bundle.get("schema_version") != 1:
        findings.append("unsupported bundle schema version")

    entry_count = bundle.get("entry_count")
    if type(entry_count) is not int or not 1 <= entry_count <= _MAX_ENTRIES:
        findings.append("bundle entry count is invalid")

    entries = bundle.get("entries")
    if not isinstance(entries, list):
        findings.append("bundle entries must be a list")
        return sorted(set(findings))
    if not 1 <= len(entries) <= _MAX_ENTRIES:
        findings.append("bundle entry count is invalid")
    if entry_count != len(entries):
        findings.append("bundle entry count mismatch")

    digest = bundle.get("bundle_sha256")
    if not _is_lower_hex(digest, 64):
        findings.append("bundle digest is invalid")

    try:
        expected = build_intelligence_bundle(entries)
    except (TypeError, ValueError):
        findings.append("invalid bundle entries")
        return sorted(set(findings))

    if digest != expected["bundle_sha256"]:
        findings.append("bundle digest mismatch")
    if entries != expected["entries"]:
        findings.append("bundle entries are not canonically ordered")
    return sorted(set(findings))
