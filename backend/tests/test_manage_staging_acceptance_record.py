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
NOW = datetime(2026, 7, 27, 22, 0, tzinfo=timezone.utc)
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "manage_staging_acceptance_record.py"
SPEC = spec_from_file_location("manage_staging_acceptance_record", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

REQUIRED_EVIDENCE = MODULE.REQUIRED_EVIDENCE
build_record = MODULE.build_record
build_receipt = MODULE.build_receipt
canonical_json = MODULE.canonical_json
validate_bundle = MODULE.validate_bundle
validate_generation_input = MODULE.validate_generation_input
validate_record = MODULE.validate_record


def evidence(candidate_sha: str = SHA):
    return [
        {
            "category": category,
            "candidate_sha": candidate_sha,
            "artifact_id": 1000 + index,
            "artifact_url": f"https://github.com/example/repo/actions/runs/1/artifacts/{1000 + index}",
            "artifact_digest": "sha256:" + f"{index + 1:064x}",
            "verified": True,
            "status": "passed",
            "observed_at": "2026-07-27T22:00:00Z",
            "summary": f"Verified {category.replace('_', ' ')} evidence.",
        }
        for index, category in enumerate(REQUIRED_EVIDENCE)
    ]


def generation_input():
    return {
        "candidate_sha": SHA,
        "selection_rationale": "Fresh protected-main candidate selected for staging acceptance.",
        "generated_at": "2026-07-27T22:00:00Z",
        "evidence": evidence(),
    }


def bundle():
    record = build_record(
        candidate_sha=SHA,
        selection_rationale="Fresh protected-main candidate selected for staging acceptance.",
        evidence=evidence(),
        generated_at=NOW,
    )
    return {"record": record, "receipt": build_receipt(record, generated_at=NOW)}


def test_record_and_receipt_are_deterministic():
    first = bundle()
    second = bundle()
    assert canonical_json(first["record"]) == canonical_json(second["record"])
    assert first == second
    assert first["record"]["decision"] == "GO"
    assert validate_bundle(first) == []


def test_incomplete_failed_or_mismatched_evidence_is_receipted_no_go():
    for mutator in (
        lambda items: items[0].update(status="failed"),
        lambda items: items[1].update(verified=False),
        lambda items: items[2].update(candidate_sha="b" * 40),
    ):
        changed = evidence()
        mutator(changed)
        record = build_record(
            candidate_sha=SHA,
            selection_rationale="Candidate remains blocked by staging evidence.",
            evidence=changed,
            generated_at=NOW,
        )
        assert record["decision"] == "NO-GO"
        payload = {"record": record, "receipt": build_receipt(record, generated_at=NOW)}
        assert validate_bundle(payload) == []


def test_rejects_missing_duplicate_and_extra_categories():
    invalid_sets = (
        evidence()[:-1],
        evidence()[:-1] + [evidence()[0]],
        evidence() + [{**evidence()[0], "category": "other"}],
    )
    for changed in invalid_sets:
        with pytest.raises(ValueError):
            build_record(
                candidate_sha=SHA,
                selection_rationale="Invalid evidence set.",
                evidence=changed,
                generated_at=NOW,
            )


def test_rejects_malformed_artifacts_sensitive_fields_and_decision_drift():
    changed = evidence()
    changed[0]["artifact_digest"] = "bad"
    with pytest.raises(ValueError):
        build_record(
            candidate_sha=SHA,
            selection_rationale="Malformed digest.",
            evidence=changed,
            generated_at=NOW,
        )

    payload = bundle()
    payload["record"]["api_key"] = "must-not-exist"
    findings = validate_bundle(payload)
    assert any("prohibited sensitive field" in finding for finding in findings)

    payload = bundle()
    payload["record"]["decision"] = "NO-GO"
    assert "record decision mismatch" in validate_bundle(payload)


def test_rejects_receipt_substitution_and_record_mutation():
    payload = bundle()
    payload["receipt"]["candidate_sha"] = "b" * 40
    assert "candidate SHA mismatch" in validate_bundle(payload)

    payload = bundle()
    payload["record"]["selection_rationale"] = "Changed after receipt."
    assert "record digest mismatch" in validate_bundle(payload)


def test_generation_input_validation_and_non_mutation():
    value = generation_input()
    original = deepcopy(value)
    assert validate_generation_input(value) == []
    assert value == original

    changed = generation_input()
    changed["generated_at"] = "2026-07-27T22:00:00+00:00"
    assert "generated_at must be a valid UTC timestamp ending in Z" in validate_generation_input(changed)

    changed = generation_input()
    changed["token"] = "not allowed"
    findings = validate_generation_input(changed)
    assert "unexpected generation input field: token" in findings
    assert any("prohibited sensitive field" in finding for finding in findings)


def test_cli_generates_valid_go_bundle(tmp_path: Path):
    source = tmp_path / "input.json"
    output = tmp_path / "acceptance.json"
    source.write_text(json.dumps(generation_input()), encoding="utf-8")
    generated = subprocess.run(
        [sys.executable, str(SCRIPT), "generate", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["record"]["decision"] == "GO"
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
    source_payload["evidence"][0]["status"] = "incomplete"
    source = tmp_path / "input.json"
    output = tmp_path / "acceptance.json"
    source.write_text(json.dumps(source_payload), encoding="utf-8")
    generated = subprocess.run(
        [sys.executable, str(SCRIPT), "generate", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 2
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["record"]["decision"] == "NO-GO"
    assert validate_bundle(payload) == []
