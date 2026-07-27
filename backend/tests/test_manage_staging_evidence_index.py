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
NOW = datetime(2026, 7, 27, 23, 0, tzinfo=timezone.utc)
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "manage_staging_evidence_index.py"
SPEC = spec_from_file_location("manage_staging_evidence_index", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

REQUIRED_ENTRIES = MODULE.REQUIRED_ENTRIES
build_index = MODULE.build_index
build_receipt = MODULE.build_receipt
canonical_json = MODULE.canonical_json
validate_bundle = MODULE.validate_bundle
validate_generation_input = MODULE.validate_generation_input
validate_index = MODULE.validate_index


def entries(candidate_sha: str = SHA):
    values = []
    for index, category in enumerate(REQUIRED_ENTRIES):
        decision = "GO" if category == "staging_acceptance_record" else "NOT-APPLICABLE"
        values.append(
            {
                "category": category,
                "candidate_sha": candidate_sha,
                "artifact_id": 1000 + index,
                "artifact_url": f"https://github.com/example/repo/actions/runs/1/artifacts/{1000 + index}",
                "artifact_digest": "sha256:" + f"{index + 1:064x}",
                "workflow_run_id": 2000 + index,
                "verified": True,
                "status": "passed",
                "decision": decision,
                "observed_at": "2026-07-27T23:00:00Z",
                "summary": f"Verified {category.replace('_', ' ')} evidence.",
            }
        )
    return values


def generation_input():
    return {
        "candidate_sha": SHA,
        "selection_rationale": "Fresh protected-main candidate selected for staging evidence indexing.",
        "generated_at": "2026-07-27T23:00:00Z",
        "entries": entries(),
    }


def bundle():
    index = build_index(
        candidate_sha=SHA,
        selection_rationale="Fresh protected-main candidate selected for staging evidence indexing.",
        entries=entries(),
        generated_at=NOW,
    )
    return {"index": index, "receipt": build_receipt(index, generated_at=NOW)}


def test_index_and_receipt_are_deterministic():
    first = bundle()
    second = bundle()
    assert canonical_json(first["index"]) == canonical_json(second["index"])
    assert first == second
    assert first["index"]["decision"] == "READY"
    assert validate_bundle(first) == []


def test_failed_unverified_mismatched_or_no_go_entries_are_not_ready():
    mutations = (
        lambda items: items[0].update(status="failed"),
        lambda items: items[1].update(verified=False),
        lambda items: items[2].update(candidate_sha="b" * 40),
        lambda items: next(item for item in items if item["category"] == "staging_acceptance_record").update(decision="NO-GO"),
    )
    for mutate in mutations:
        changed = entries()
        mutate(changed)
        index = build_index(
            candidate_sha=SHA,
            selection_rationale="Candidate remains blocked by staging evidence.",
            entries=changed,
            generated_at=NOW,
        )
        assert index["decision"] == "NOT-READY"
        assert validate_index(index) == []
        assert validate_bundle({"index": index, "receipt": build_receipt(index, generated_at=NOW)}) == []


def test_rejects_missing_duplicate_extra_and_malformed_entries():
    invalid_sets = (
        entries()[:-1],
        entries()[:-1] + [entries()[0]],
        entries() + [{**entries()[0], "category": "other"}],
    )
    for changed in invalid_sets:
        with pytest.raises(ValueError):
            build_index(
                candidate_sha=SHA,
                selection_rationale="Invalid entry set.",
                entries=changed,
                generated_at=NOW,
            )

    changed = entries()
    changed[0]["artifact_digest"] = "bad"
    with pytest.raises(ValueError):
        build_index(
            candidate_sha=SHA,
            selection_rationale="Malformed digest.",
            entries=changed,
            generated_at=NOW,
        )


def test_rejects_sensitive_fields_decision_drift_and_receipt_substitution():
    payload = bundle()
    payload["index"]["api_key"] = "must-not-exist"
    findings = validate_bundle(payload)
    assert any("prohibited sensitive field" in finding for finding in findings)

    payload = bundle()
    payload["index"]["decision"] = "NOT-READY"
    assert "index decision mismatch" in validate_bundle(payload)

    payload = bundle()
    payload["receipt"]["candidate_sha"] = "b" * 40
    assert "candidate SHA mismatch" in validate_bundle(payload)

    payload = bundle()
    payload["index"]["selection_rationale"] = "Changed after receipt."
    assert "index digest mismatch" in validate_bundle(payload)


def test_generation_input_is_strict_and_non_mutating():
    value = generation_input()
    original = deepcopy(value)
    assert validate_generation_input(value) == []
    assert value == original

    changed = generation_input()
    changed["generated_at"] = "2026-07-27T23:00:00+00:00"
    assert "generated_at must be a valid UTC timestamp ending in Z" in validate_generation_input(changed)

    changed = generation_input()
    changed["token"] = "not allowed"
    findings = validate_generation_input(changed)
    assert "unexpected generation input field: token" in findings
    assert any("prohibited sensitive field" in finding for finding in findings)


def test_cli_go_and_not_ready_exit_codes(tmp_path: Path):
    source = tmp_path / "input.json"
    output = tmp_path / "index.json"
    source.write_text(json.dumps(generation_input()), encoding="utf-8")
    generated = subprocess.run(
        [sys.executable, str(SCRIPT), "generate", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0
    assert json.loads(output.read_text(encoding="utf-8"))["index"]["decision"] == "READY"

    payload = generation_input()
    payload["entries"][0]["status"] = "incomplete"
    source.write_text(json.dumps(payload), encoding="utf-8")
    generated = subprocess.run(
        [sys.executable, str(SCRIPT), "generate", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 2
    assert json.loads(output.read_text(encoding="utf-8"))["index"]["decision"] == "NOT-READY"

    validated = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validated.returncode == 0
    assert json.loads(validated.stdout)["valid"] is True
