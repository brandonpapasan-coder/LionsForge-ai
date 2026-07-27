from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from scripts.manage_staging_candidate_manifest import (
    REQUIRED_WORKFLOWS,
    build_manifest,
    build_receipt,
    canonical_json,
    validate_bundle,
    validate_manifest,
)

SHA = "a" * 40
NOW = datetime(2026, 7, 27, 20, 0, tzinfo=timezone.utc)


def runs(sha: str = SHA):
    return [
        {
            "name": name,
            "run_id": 1000 + index,
            "run_number": 200 + index,
            "status": "completed",
            "conclusion": "success",
            "head_sha": sha,
        }
        for index, name in enumerate(REQUIRED_WORKFLOWS)
    ]


def bundle():
    manifest = build_manifest(
        candidate_sha=SHA,
        selection_rationale="Fresh protected-main candidate selected after the latest merged launch-critical change.",
        ancestry_verified=True,
        workflows=runs(),
        generated_at=NOW,
    )
    return {"manifest": manifest, "receipt": build_receipt(manifest, generated_at=NOW)}


def test_manifest_and_receipt_are_deterministic():
    first = bundle()
    second = bundle()
    assert canonical_json(first["manifest"]) == canonical_json(second["manifest"])
    assert first == second
    assert first["manifest"]["decision"] == "GO"
    assert validate_bundle(first) == []


def test_manifest_fails_closed_without_ancestry_proof():
    manifest = build_manifest(
        candidate_sha=SHA,
        selection_rationale="Candidate awaiting protected-main ancestry verification.",
        ancestry_verified=False,
        workflows=runs(),
        generated_at=NOW,
    )
    assert manifest["decision"] == "NO-GO"
    assert validate_manifest(manifest) == []


def test_rejects_missing_duplicate_extra_and_unsuccessful_workflows():
    for changed in (
        runs()[:-1],
        runs()[:-1] + [runs()[0]],
        runs() + [{**runs()[0], "name": "Other CI"}],
    ):
        with pytest.raises(ValueError):
            build_manifest(candidate_sha=SHA, selection_rationale="Valid rationale", ancestry_verified=True, workflows=changed, generated_at=NOW)

    failed = runs()
    failed[0]["conclusion"] = "failure"
    manifest = build_manifest(candidate_sha=SHA, selection_rationale="Valid rationale", ancestry_verified=True, workflows=failed, generated_at=NOW)
    assert manifest["decision"] == "NO-GO"


def test_rejects_workflow_head_substitution_and_receipt_substitution():
    mismatched = runs()
    mismatched[2]["head_sha"] = "b" * 40
    manifest = build_manifest(candidate_sha=SHA, selection_rationale="Valid rationale", ancestry_verified=True, workflows=mismatched, generated_at=NOW)
    assert manifest["decision"] == "NO-GO"

    payload = bundle()
    payload["receipt"]["candidate_sha"] = "b" * 40
    assert "candidate SHA mismatch" in validate_bundle(payload)


def test_rejects_invalid_sha_private_fields_ordering_and_decision_drift():
    with pytest.raises(ValueError):
        build_manifest(candidate_sha="ABC", selection_rationale="Valid rationale", ancestry_verified=True, workflows=runs(), generated_at=NOW)

    payload = bundle()
    payload["manifest"]["api_key"] = "should-not-exist"
    findings = validate_bundle(payload)
    assert any("prohibited sensitive field" in finding for finding in findings)

    payload = bundle()
    payload["manifest"]["workflow_runs"] = list(reversed(payload["manifest"]["workflow_runs"]))
    assert "workflow run ordering is not deterministic" in validate_bundle(payload)

    payload = bundle()
    payload["manifest"]["decision"] = "NO-GO"
    assert "manifest decision mismatch" in validate_bundle(payload)


def test_bundle_structure_and_digest_are_strict():
    assert validate_bundle({"manifest": {}}) == ["bundle fields are invalid"]
    payload = bundle()
    payload["manifest"]["selection_rationale"] = "Changed after receipt"
    assert "manifest digest mismatch" in validate_bundle(payload)
