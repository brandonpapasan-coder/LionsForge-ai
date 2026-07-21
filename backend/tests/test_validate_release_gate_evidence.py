import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_release_gate_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

REPOSITORY = "owner/repository"
SHA = "a" * 40


def gate(name, *, state="success", run_id=1):
    base = {
        "name": name,
        "path": MODULE.REQUIRED_WORKFLOW_PATHS[name],
    }
    if state == "missing":
        return {
            **base,
            "status": "missing",
            "conclusion": None,
            "run_id": None,
            "html_url": None,
            "event": None,
            "head_branch": None,
            "head_sha": None,
        }
    status = "completed" if state in {"success", "failure"} else "in_progress"
    conclusion = state if state in {"success", "failure"} else None
    return {
        **base,
        "status": status,
        "conclusion": conclusion,
        "run_id": run_id,
        "html_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
        "event": "push",
        "head_branch": "main",
        "head_sha": SHA,
    }


def payload(*, passed=True, state=None):
    gate_state = state or ("success" if passed else "missing")
    gates = [
        gate(name, state=gate_state, run_id=index)
        for index, name in enumerate(MODULE.REQUIRED_WORKFLOW_PATHS, start=1)
    ]
    return {
        "repository": REPOSITORY,
        "release_sha": SHA,
        "required_event": "push",
        "required_branch": "main",
        "required_workflow_paths": MODULE.REQUIRED_WORKFLOW_PATHS,
        "passed": passed,
        "gates": gates,
    }


def write_payload(path: Path, evidence=None) -> None:
    path.write_text(json.dumps(evidence or payload()), encoding="utf-8")


def test_accepts_consistent_passing_missing_and_completed_failure_evidence():
    MODULE.validate_payload(payload(passed=True), REPOSITORY, SHA)
    MODULE.validate_payload(payload(passed=False), REPOSITORY, SHA)
    MODULE.validate_payload(
        payload(passed=False, state="failure"),
        REPOSITORY,
        SHA,
    )


def test_reads_regular_utf8_json_file(tmp_path):
    evidence_path = tmp_path / "evidence.json"
    write_payload(evidence_path)
    assert MODULE._read_evidence(evidence_path) == payload()


def test_rejects_empty_oversized_and_non_utf8_files(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="must not be empty"):
        MODULE._read_evidence(empty)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * (MODULE.MAX_EVIDENCE_BYTES + 1))
    with pytest.raises(ValueError, match="safety limit"):
        MODULE._read_evidence(oversized)

    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="valid UTF-8"):
        MODULE._read_evidence(invalid_utf8)


def test_rejects_malformed_json_and_non_regular_targets(tmp_path):
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed JSON"):
        MODULE._read_evidence(malformed)

    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(ValueError, match="regular file"):
        MODULE._read_evidence(directory)


def test_rejects_symbolic_link_evidence(tmp_path):
    target = tmp_path / "target.json"
    write_payload(target)
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symbolic link"):
        MODULE._read_evidence(link)


def test_rejects_file_replacement_before_open(tmp_path, monkeypatch):
    evidence_path = tmp_path / "evidence.json"
    write_payload(evidence_path)
    real_open = os.open

    def replacing_open(path, flags):
        replacement = tmp_path / "replacement.json"
        write_payload(replacement, payload(passed=False))
        replacement.replace(evidence_path)
        return real_open(path, flags)

    monkeypatch.setattr(MODULE.os, "open", replacing_open)
    with pytest.raises(ValueError, match="changed before"):
        MODULE._read_evidence(evidence_path)


def test_rejects_truncation_during_read(tmp_path, monkeypatch):
    evidence_path = tmp_path / "evidence.json"
    write_payload(evidence_path)
    real_read = os.read

    def truncated_read(descriptor, count):
        body = real_read(descriptor, count)
        return body[:-1]

    monkeypatch.setattr(MODULE.os, "read", truncated_read)
    with pytest.raises(ValueError, match="truncated during reading"):
        MODULE._read_evidence(evidence_path)


def test_rejects_top_level_field_changes():
    evidence = payload()
    evidence["unexpected"] = True
    with pytest.raises(ValueError, match="top-level fields"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)


def test_rejects_repository_and_sha_mismatches():
    evidence = payload()
    evidence["repository"] = "other/repository"
    with pytest.raises(ValueError, match="repository does not match"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload()
    evidence["release_sha"] = "b" * 40
    with pytest.raises(ValueError, match="release_sha does not match"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)


def test_rejects_gate_reordering_and_path_spoofing():
    evidence = payload()
    evidence["gates"][0], evidence["gates"][1] = (
        evidence["gates"][1],
        evidence["gates"][0],
    )
    with pytest.raises(ValueError, match="identity or path"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload()
    evidence["gates"][0]["path"] = ".github/workflows/spoofed.yml"
    with pytest.raises(ValueError, match="identity or path"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)


def test_rejects_unknown_status_conclusion_and_premature_conclusion():
    evidence = payload()
    evidence["gates"][0]["status"] = "invented"
    with pytest.raises(ValueError, match="status is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload()
    evidence["gates"][0]["conclusion"] = "invented"
    with pytest.raises(ValueError, match="conclusion is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload(passed=False, state="in_progress")
    evidence["gates"][0]["conclusion"] = "success"
    with pytest.raises(ValueError, match="must be null before completion"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)


def test_rejects_incoherent_missing_evidence():
    evidence = payload(passed=False)
    evidence["gates"][0]["status"] = "in_progress"
    with pytest.raises(ValueError, match="missing evidence status"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload(passed=False)
    evidence["gates"][0]["html_url"] = "https://github.com/owner/repository/actions/runs/1"
    with pytest.raises(ValueError, match="missing evidence has invalid html_url"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)


def test_rejects_invalid_run_identity_and_url_binding():
    evidence = payload()
    evidence["gates"][0]["run_id"] = True
    with pytest.raises(ValueError, match="run_id is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload()
    evidence["gates"][0]["html_url"] = (
        "https://github.com/other/repository/actions/runs/1"
    )
    with pytest.raises(ValueError, match="html_url is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload()
    evidence["gates"][0]["html_url"] = (
        "https://github.com/owner/repository/actions/runs/999"
    )
    with pytest.raises(ValueError, match="html_url is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)


def test_rejects_duplicate_run_ids_and_urls_across_gates():
    evidence = payload()
    evidence["gates"][1]["run_id"] = evidence["gates"][0]["run_id"]
    evidence["gates"][1]["html_url"] = evidence["gates"][0]["html_url"]
    with pytest.raises(ValueError, match="reuses a prior run_id"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload(passed=False, state="failure")
    evidence["gates"][2]["run_id"] = evidence["gates"][1]["run_id"]
    evidence["gates"][2]["html_url"] = evidence["gates"][1]["html_url"]
    with pytest.raises(ValueError, match="reuses a prior run_id"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)


def test_rejects_invalid_event_branch_and_sha_binding():
    evidence = payload()
    evidence["gates"][0]["event"] = "pull_request"
    with pytest.raises(ValueError, match="event is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload()
    evidence["gates"][0]["head_branch"] = "dev/test"
    with pytest.raises(ValueError, match="head_branch is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload()
    evidence["gates"][0]["head_sha"] = "b" * 40
    with pytest.raises(ValueError, match="head_sha is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)


def test_rejects_inconsistent_passed_value():
    evidence = payload(passed=True)
    evidence["passed"] = False
    with pytest.raises(ValueError, match="passed value is inconsistent"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload(passed=False)
    evidence["passed"] = True
    with pytest.raises(ValueError, match="passed value is inconsistent"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)
