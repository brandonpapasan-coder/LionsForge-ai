"""Deterministic self-contained archives for intelligence comparisons."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .comparison_receipt import validate_intelligence_comparison_receipt

_ARCHIVE_SCHEMA = "lionsforge.internal-alpha-intelligence-comparison-archive"
_ARCHIVE_KEYS = {
    "schema",
    "schema_version",
    "baseline",
    "candidate",
    "comparison",
    "receipt",
    "archive_sha256",
    "interpretation_notice",
}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_NOTICE = (
    "This archive preserves deterministic internal-alpha comparison evidence only and does not "
    "infer causality or authorize any release transition."
)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _archive_body(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    comparison: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": _ARCHIVE_SCHEMA,
        "schema_version": 1,
        "baseline": baseline,
        "candidate": candidate,
        "comparison": comparison,
        "receipt": receipt,
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    comparison: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Build an archive only from an exactly validated receipt chain."""
    findings = validate_intelligence_comparison_receipt(
        receipt,
        comparison,
        baseline,
        candidate,
    )
    if findings:
        raise ValueError("invalid comparison receipt chain: " + "; ".join(findings))
    body = _archive_body(baseline, candidate, comparison, receipt)
    return {
        **body,
        "archive_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive(archive: dict[str, Any]) -> list[str]:
    """Validate archive shape, embedded receipt chain, and exact archive digest."""
    if not isinstance(archive, dict):
        return ["comparison archive must be an object"]

    findings: list[str] = []
    if set(archive) != _ARCHIVE_KEYS:
        findings.append("comparison archive keys invalid")
    if archive.get("schema") != _ARCHIVE_SCHEMA:
        findings.append("comparison archive schema mismatch")

    schema_version = archive.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        findings.append("comparison archive schema version mismatch")
    if archive.get("interpretation_notice") != _NOTICE:
        findings.append("comparison archive interpretation_notice mismatch")

    archive_digest = archive.get("archive_sha256")
    if not isinstance(archive_digest, str) or not _SHA256_PATTERN.fullmatch(
        archive_digest
    ):
        findings.append("comparison archive digest invalid")

    baseline = archive.get("baseline")
    candidate = archive.get("candidate")
    comparison = archive.get("comparison")
    receipt = archive.get("receipt")
    if not all(isinstance(value, dict) for value in (baseline, candidate, comparison, receipt)):
        findings.append("comparison archive payload objects invalid")
        return findings

    try:
        findings.extend(
            validate_intelligence_comparison_receipt(
                receipt,
                comparison,
                baseline,
                candidate,
            )
        )
        body = _archive_body(baseline, candidate, comparison, receipt)
        expected_digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    except (KeyError, TypeError, ValueError):
        findings.append("comparison archive payload invalid")
        return findings

    if archive_digest != expected_digest:
        findings.append("comparison archive digest mismatch")
    return findings
