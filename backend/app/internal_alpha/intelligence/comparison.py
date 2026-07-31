"""Deterministic comparisons for validated internal-alpha intelligence bundles."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .bundle import validate_intelligence_bundle

_COMPARISON_SCHEMA = "lionsforge.internal-alpha-intelligence-comparison"


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


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
