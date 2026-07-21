import importlib.util
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


def gate(name, *, passed=True, run_id=1):
    return {
        "name": name,
        "path": MODULE.REQUIRED_WORKFLOW_PATHS[name],
        "status": "completed" if passed else "in_progress",
        "conclusion": "success" if passed else None,
        "run_id": run_id if passed else None,
        "html_url": f"https://github.com/owner/repository/actions/runs/{run_id}"
        if passed
        else None,
        "event": "push" if passed else None,
        "head_branch": "main" if passed else None,
        "head_sha": SHA if passed else None,
    }


def payload(*, passed=True):
    gates = [
        gate(name, passed=passed, run_id=index)
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


def test_accepts_consistent_passing_and_failing_evidence():
    MODULE.validate_payload(payload(passed=True), REPOSITORY, SHA)
    MODULE.validate_payload(payload(passed=False), REPOSITORY, SHA)


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


def test_rejects_invalid_gate_fields():
    evidence = payload()
    evidence["gates"][0]["run_id"] = True
    with pytest.raises(ValueError, match="run_id is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload()
    evidence["gates"][0]["html_url"] = "https://example.test/run/1"
    with pytest.raises(ValueError, match="html_url is invalid"):
        MODULE.validate_payload(evidence, REPOSITORY, SHA)

    evidence = payload()
    evidence["gates"][0]["head_sha"] = "not-a-sha"
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
