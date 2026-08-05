"""Deterministic comparisons for validated internal-alpha intelligence bundles."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .bundle import validate_intelligence_bundle

_COMPARISON_SCHEMA = "lionsforge.internal-alpha-intelligence-comparison"
_COMPARISON_FIELDS = {
    "schema",
    "schema_version",
    "baseline_bundle_sha256",
    "candidate_bundle_sha256",
    "added_candidates",
    "removed_candidates",
    "changed_candidates",
    "unchanged_candidate_count",
    "interpretation_notice",
    "comparison_sha256",
}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _is_candidate_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and all(
            isinstance(candidate, str)
            and _CANDIDATE_PATTERN.fullmatch(candidate) is not None
            for candidate in value
        )
        and value == sorted(set(value))
    )


def compare_intelligence_bundles(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    """Compare two valid bundles without making causal or release claims."""
    baseline_findings = validate_intelligence_bundle(baseline)
    candidate_findings = validate_intelligence_bundle(candidate)
    if baseline_findings:
        raise ValueError("invalid baseline bundle: " + "; ".join(baseline_findings))
    if candidate_findings:
        raise ValueError("invalid candidate bundle: " + "; ".join(candidate_findings))

    baseline_entries = {
        entry["report"]["candidate_sha"]: entry for entry in baseline["entries"]
    }
    candidate_entries = {
        entry["report"]["candidate_sha"]: entry for entry in candidate["entries"]
    }
    baseline_shas = set(baseline_entries)
    candidate_shas = set(candidate_entries)
    shared = baseline_shas & candidate_shas
    changed = sorted(
        sha for sha in shared if baseline_entries[sha] != candidate_entries[sha]
    )
    body = {
        "schema": _COMPARISON_SCHEMA,
        "schema_version": 1,
        "baseline_bundle_sha256": baseline["bundle_sha256"],
        "candidate_bundle_sha256": candidate["bundle_sha256"],
        "added_candidates": sorted(candidate_shas - baseline_shas),
        "removed_candidates": sorted(baseline_shas - candidate_shas),
        "changed_candidates": changed,
        "unchanged_candidate_count": len(shared) - len(changed),
        "interpretation_notice": (
            "This comparison reports deterministic payload differences only and does not infer "
            "causality or authorize any release transition."
        ),
    }
    return {
        **body,
        "comparison_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison(
    comparison: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[str]:
    """Return deterministic findings for drifted or substituted comparisons."""
    findings: list[str] = []
    if set(comparison) != _COMPARISON_FIELDS:
        findings.append("comparison fields mismatch")
    if comparison.get("schema") != _COMPARISON_SCHEMA:
        findings.append("unsupported comparison schema")
    schema_version = comparison.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != 1:
        findings.append("unsupported comparison schema version")
    if not _is_sha256(comparison.get("baseline_bundle_sha256")):
        findings.append("invalid baseline bundle digest")
    if not _is_sha256(comparison.get("candidate_bundle_sha256")):
        findings.append("invalid candidate bundle digest")
    if not _is_sha256(comparison.get("comparison_sha256")):
        findings.append("invalid comparison digest")
    if not _is_candidate_list(comparison.get("added_candidates")):
        findings.append("invalid added candidate list")
    if not _is_candidate_list(comparison.get("removed_candidates")):
        findings.append("invalid removed candidate list")
    if not _is_candidate_list(comparison.get("changed_candidates")):
        findings.append("invalid changed candidate list")
    unchanged_count = comparison.get("unchanged_candidate_count")
    if (
        isinstance(unchanged_count, bool)
        or not isinstance(unchanged_count, int)
        or unchanged_count < 0
    ):
        findings.append("invalid unchanged candidate count")
    if not isinstance(comparison.get("interpretation_notice"), str):
        findings.append("invalid comparison interpretation notice")

    try:
        expected = compare_intelligence_bundles(baseline, candidate)
    except ValueError as exc:
        findings.append(str(exc))
        return sorted(set(findings))

    if comparison.get("baseline_bundle_sha256") != baseline.get("bundle_sha256"):
        findings.append("baseline bundle digest binding mismatch")
    if comparison.get("candidate_bundle_sha256") != candidate.get("bundle_sha256"):
        findings.append("candidate bundle digest binding mismatch")
    if comparison.get("comparison_sha256") != expected["comparison_sha256"]:
        findings.append("comparison digest mismatch")
    if comparison != expected:
        findings.append("comparison payload mismatch")
    return sorted(set(findings))
