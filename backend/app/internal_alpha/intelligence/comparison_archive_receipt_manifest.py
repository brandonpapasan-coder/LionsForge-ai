"""Deterministic manifests for validated comparison archive receipts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison_archive_receipt import (
    validate_intelligence_comparison_archive_receipt,
)

_MANIFEST_SCHEMA = "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest"
_MANIFEST_KEYS = {
    "schema",
    "schema_version",
    "entry_count",
    "entries",
    "manifest_sha256",
    "interpretation_notice",
}
_ENTRY_KEYS = {"archive", "receipt"}
_NOTICE = (
    "This manifest preserves bounded comparison archive receipt evidence only and does not infer "
    "causality or authorize any release transition."
)
_MAX_ENTRIES = 100


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _validated_entry(entry: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
        raise ValueError("comparison archive receipt manifest entry keys invalid")
    archive = entry.get("archive")
    receipt = entry.get("receipt")
    if not isinstance(archive, dict) or not isinstance(receipt, dict):
        raise ValueError("comparison archive receipt manifest entry payload invalid")
    findings = validate_intelligence_comparison_archive_receipt(receipt, archive)
    if findings:
        raise ValueError("invalid comparison archive receipt entry: " + "; ".join(findings))
    archive_sha256 = archive.get("archive_sha256")
    if not isinstance(archive_sha256, str):
        raise ValueError("comparison archive receipt manifest archive digest invalid")
    return archive_sha256, {"archive": archive, "receipt": receipt}


def _manifest_body(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": _MANIFEST_SCHEMA,
        "schema_version": 1,
        "entry_count": len(entries),
        "entries": entries,
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_receipt_manifest(
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one bounded, canonically ordered manifest from valid archive receipts."""
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ENTRIES:
        raise ValueError("comparison archive receipt manifest entries must contain 1 to 100 items")

    validated = [_validated_entry(entry) for entry in entries]
    archive_digests = [digest for digest, _ in validated]
    if len(set(archive_digests)) != len(archive_digests):
        raise ValueError("comparison archive receipt manifest contains duplicate archives")

    ordered_entries = [entry for _, entry in sorted(validated, key=lambda item: item[0])]
    body = _manifest_body(ordered_entries)
    return {
        **body,
        "manifest_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt_manifest(
    manifest: dict[str, Any],
) -> list[str]:
    """Validate manifest shape, ordering, receipt chains, uniqueness, and digest fail closed."""
    if not isinstance(manifest, dict):
        return ["comparison archive receipt manifest must be an object"]

    findings: list[str] = []
    if set(manifest) != _MANIFEST_KEYS:
        findings.append("comparison archive receipt manifest keys invalid")
    if manifest.get("schema") != _MANIFEST_SCHEMA:
        findings.append("comparison archive receipt manifest schema mismatch")
    if manifest.get("schema_version") != 1:
        findings.append("comparison archive receipt manifest schema version mismatch")
    if manifest.get("interpretation_notice") != _NOTICE:
        findings.append("comparison archive receipt manifest interpretation_notice mismatch")

    entries = manifest.get("entries")
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ENTRIES:
        findings.append("comparison archive receipt manifest entries invalid")
        return findings
    if manifest.get("entry_count") != len(entries):
        findings.append("comparison archive receipt manifest entry_count mismatch")

    validated: list[tuple[str, dict[str, Any]]] = []
    for index, entry in enumerate(entries):
        try:
            validated.append(_validated_entry(entry))
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(f"comparison archive receipt manifest entry {index} invalid: {exc}")

    if len(validated) == len(entries):
        archive_digests = [digest for digest, _ in validated]
        if len(set(archive_digests)) != len(archive_digests):
            findings.append("comparison archive receipt manifest contains duplicate archives")
        if archive_digests != sorted(archive_digests):
            findings.append("comparison archive receipt manifest entries not canonically ordered")

    try:
        body = _manifest_body(entries)
        expected_digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    except (TypeError, ValueError):
        findings.append("comparison archive receipt manifest payload invalid")
        return findings
    if manifest.get("manifest_sha256") != expected_digest:
        findings.append("comparison archive receipt manifest digest mismatch")
    return findings
