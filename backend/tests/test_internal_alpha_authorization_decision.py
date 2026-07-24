import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "manage_internal_alpha_authorization_decision.py"
SPEC = spec_from_file_location("manage_internal_alpha_authorization_decision", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
build_decision = MODULE.build_decision
write_decision = MODULE.write_decision
verify_decision = MODULE.verify_decision
STEPS = MODULE.STEPS


def values(outcome: str = "success") -> dict:
    return {
        "repository": "brandonpapasan-coder/LionsForge-ai",
        "run_id": 123,
        "run_attempt": 1,
        "workflow_sha": "a" * 40,
        "candidate_sha": "b" * 40,
        "backend_digest": "sha256:" + "c" * 64,
        "frontend_digest": "sha256:" + "d" * 64,
        "raw_steps": [f"{name}={outcome}" for name in STEPS],
    }


def test_all_success_is_authorized_and_deterministic(tmp_path: Path):
    payload = build_decision(**values())
    assert payload["authorized"] is True
    assert payload["failed_steps"] == []
    path = tmp_path / "decision.json"
    write_decision(path, payload)
    first = path.read_bytes()
    write_decision(path, payload)
    assert path.read_bytes() == first
    verify_decision(path, payload)


def test_any_non_success_is_fail_closed():
    kwargs = values()
    kwargs["raw_steps"][3] = f"{STEPS[3]}=skipped"
    payload = build_decision(**kwargs)
    assert payload["authorized"] is False
    assert payload["failed_steps"] == [STEPS[3]]


def test_rejects_missing_reordered_and_invalid_outcomes():
    kwargs = values()
    kwargs["raw_steps"] = kwargs["raw_steps"][:-1]
    with pytest.raises(ValueError, match="all canonical"):
        build_decision(**kwargs)
    kwargs = values()
    kwargs["raw_steps"][0], kwargs["raw_steps"][1] = (
        kwargs["raw_steps"][1],
        kwargs["raw_steps"][0],
    )
    with pytest.raises(ValueError, match="canonical names"):
        build_decision(**kwargs)
    kwargs = values()
    kwargs["raw_steps"][0] = f"{STEPS[0]}=unknown"
    with pytest.raises(ValueError, match="invalid outcome"):
        build_decision(**kwargs)


def test_rejects_boolean_run_identifiers_and_bad_provenance():
    for field in ("run_id", "run_attempt"):
        kwargs = values()
        kwargs[field] = True
        with pytest.raises(ValueError, match="positive integer"):
            build_decision(**kwargs)
    kwargs = values()
    kwargs["workflow_sha"] = "A" * 40
    with pytest.raises(ValueError, match="workflow SHA"):
        build_decision(**kwargs)


def test_verification_rejects_mutation_and_false_positive(tmp_path: Path):
    kwargs = values()
    kwargs["raw_steps"][2] = f"{STEPS[2]}=failure"
    payload = build_decision(**kwargs)
    path = tmp_path / "decision.json"
    write_decision(path, payload)
    altered = json.loads(path.read_text(encoding="utf-8"))
    altered["authorized"] = True
    altered["failed_steps"] = []
    path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        verify_decision(path, payload)


def test_rejects_weakened_boundary_via_record_mutation(tmp_path: Path):
    payload = build_decision(**values())
    path = tmp_path / "decision.json"
    write_decision(path, payload)
    altered = json.loads(path.read_text(encoding="utf-8"))
    altered["authorization_scope"]["public_access_authorized"] = True
    path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        verify_decision(path, payload)
