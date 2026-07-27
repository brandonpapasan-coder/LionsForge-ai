from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

SHA = "a" * 40
NOW = datetime(2026, 7, 27, 20, 0, tzinfo=timezone.utc)
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "manage_staging_candidate_manifest.py"
SPEC = spec_from_file_location("manage_staging_candidate_manifest", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

REQUIRED_WORKFLOWS = MODULE.REQUIRED_WORKFLOWS
build_manifest = MODULE.build_manifest
build_receipt = MODULE.build_receipt
canonical_json = MODULE.canonical_json
validate_bundle = MODULE.validate_bundle
validate_generation_input = MODULE.validate_generation_input
validate_manifest = MODULE.validate_manifest


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


def generation_input():
    return {
        "candidate_sha": SHA,
        "selection_rationale": "Fresh protected-main candidate selected after the latest merged launch-critical change.",
        "protected_main_ancestry_verified": True,
        "generated_at": "2026-07-27T20:00:00Z",
        "workflow_runs": runs(),
    }


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


def test_generation_input_matches_preflight_contract():
    assert validate_generation_input(generation_input()) == []
    changed = generation_input()
    changed["workflow_runs"][0]["head_sha"] = "b" * 40
    assert validate_generation_input(changed) == []


def test_generation_input_rejects_shape_timestamp_and_sensitive_fields():
    assert validate_generation_input([]) == ["generation input must be an object"]

    changed = generation_input()
    changed["generated_at"] = "not-a-timestamp"
    assert "generated_at must be a valid UTC timestamp string" in validate_generation_input(changed)

    changed = generation_input()
    changed["token"] = "not allowed"
    findings = validate_generation_input(changed)
    assert "unexpected generation input field: token" in findings
    assert any("prohibited sensitive field" in finding for finding in findings)


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


def test_cli_generates_and_validates_go_bundle(tmp_path: Path):
    source = tmp_path / "input.json"
    output = tmp_path / "manifest.json"
    source.write_text(json.dumps(generation_input()), encoding="utf-8")
    generated = subprocess.run(
        [sys.executable, str(SCRIPT), "generate", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["manifest"]["decision"] == "GO"
    assert validate_bundle(payload) == []

    validated = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validated.returncode == 0
    assert json.loads(validated.stdout)["valid"] is True


def test_cli_returns_two_for_valid_no_go_bundle(tmp_path: Path):
    source_payload = generation_input()
    source_payload["protected_main_ancestry_verified"] = False
    source = tmp_path / "input.json"
    output = tmp_path / "manifest.json"
    source.write_text(json.dumps(source_payload), encoding="utf-8")
    generated = subprocess.run(
        [sys.executable, str(SCRIPT), "generate", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 2
    assert json.loads(output.read_text(encoding="utf-8"))["manifest"]["decision"] == "NO-GO"


def test_cli_rejects_unexpected_generation_fields(tmp_path: Path):
    source_payload = generation_input()
    source_payload["token"] = "not allowed"
    source = tmp_path / "input.json"
    output = tmp_path / "manifest.json"
    source.write_text(json.dumps(source_payload), encoding="utf-8")
    generated = subprocess.run(
        [sys.executable, str(SCRIPT), "generate", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode != 0
    assert not output.exists()


def test_generation_input_is_not_mutated():
    value = generation_input()
    original = deepcopy(value)
    assert validate_generation_input(value) == []
    assert value == original
