from __future__ import annotations

import hashlib
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_activation_binding.py"
SPEC = spec_from_file_location("validate_public_operations_activation_binding", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def build(tmp_path: Path, decision: str = "NO-GO") -> dict[str, object]:
    evidence = [
        {"type": "public-data-inventory", "path": "a", "sha256": "1" * 64, "required_decision": decision},
        {"type": "support-escalation-readiness", "path": "b", "sha256": "2" * 64, "required_decision": decision},
        {"type": "privacy-request-readiness", "path": "c", "sha256": "3" * 64, "required_decision": decision},
        {"type": "incident-communication-readiness", "path": "d", "sha256": "4" * 64, "required_decision": decision},
    ]
    manifest = {"candidate_sha": "0" * 40, "decision": decision, "evidence": evidence}
    raw = json.dumps(manifest, sort_keys=True).encode()
    path = tmp_path / "manifest.json"
    path.write_bytes(raw)
    aggregate = MODULE._aggregate(manifest)
    return {
        "schema": "lionsforge.public-operations-activation-binding",
        "schema_version": 1,
        "candidate_sha": "0" * 40,
        "decision": decision,
        "activation_mode": "NONE" if decision == "NO-GO" else "CONTROLLED-BETA",
        "manifest_path": path.name,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "aggregate_evidence_sha256": aggregate,
        "authorization_owner_role": "Public operations owner role",
        "independent_approver_role": "Independent release approver role",
        "authorized_at": "2026-07-29T00:00:00Z",
    }


def test_valid_no_go_binding(tmp_path: Path) -> None:
    result = MODULE.validate_record(build(tmp_path), tmp_path, "0" * 40)
    assert result["result"] == "VALID"
    assert result["activation_mode"] == "NONE"


def test_rejects_digest_candidate_and_role_drift(tmp_path: Path) -> None:
    value = build(tmp_path)
    value["manifest_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="manifest digest mismatch"):
        MODULE.validate_record(value, tmp_path)
    value = build(tmp_path)
    with pytest.raises(ValueError, match="expected candidate"):
        MODULE.validate_record(value, tmp_path, "a" * 40)
    value = build(tmp_path)
    value["independent_approver_role"] = value["authorization_owner_role"]
    with pytest.raises(ValueError, match="roles must be separated"):
        MODULE.validate_record(value, tmp_path)


def test_rejects_decision_mode_and_aggregate_drift(tmp_path: Path) -> None:
    value = build(tmp_path)
    value["activation_mode"] = "CONTROLLED-BETA"
    with pytest.raises(ValueError, match="NO-GO requires"):
        MODULE.validate_record(value, tmp_path)
    value = build(tmp_path)
    value["aggregate_evidence_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="aggregate evidence digest mismatch"):
        MODULE.validate_record(value, tmp_path)
