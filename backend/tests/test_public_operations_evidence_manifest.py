from __future__ import annotations

import copy
import hashlib
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_evidence_manifest.py"
SPEC = spec_from_file_location("validate_public_operations_evidence_manifest", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

TYPES = [
    "public-data-inventory",
    "support-escalation-readiness",
    "privacy-request-readiness",
    "incident-communication-readiness",
]


def build(tmp_path: Path, decision: str = "NO-GO") -> dict[str, object]:
    evidence = []
    for index, evidence_type in enumerate(TYPES):
        path = tmp_path / f"record-{index}.json"
        payload = json.dumps({"candidate_sha": "0" * 40, "decision": decision}, sort_keys=True).encode()
        path.write_bytes(payload)
        evidence.append(
            {
                "type": evidence_type,
                "path": path.name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "required_decision": decision,
            }
        )
    return {
        "schema": "lionsforge.public-operations-evidence-manifest",
        "schema_version": 1,
        "candidate_sha": "0" * 40,
        "decision": decision,
        "owner_role": "Public operations launch owner role",
        "evidence": evidence,
    }


def test_manifest_verifies_bytes_candidate_and_decisions(tmp_path: Path) -> None:
    report = MODULE.validate_manifest(build(tmp_path), tmp_path, "0" * 40)
    assert report["evidence_count"] == 4
    assert report["decision"] == "NO-GO"
    assert len(report["aggregate_evidence_sha256"]) == 64


def test_rejects_missing_duplicate_and_candidate_mismatch(tmp_path: Path) -> None:
    value = build(tmp_path)
    value["evidence"] = value["evidence"][:-1]
    with pytest.raises(ValueError, match="required evidence types are missing"):
        MODULE.validate_structure(value)
    value = build(tmp_path)
    value["evidence"].append(copy.deepcopy(value["evidence"][0]))
    with pytest.raises(ValueError, match="duplicate evidence type"):
        MODULE.validate_structure(value)
    with pytest.raises(ValueError, match="does not match expected candidate"):
        MODULE.validate_structure(build(tmp_path), "a" * 40)


def test_rejects_digest_path_and_decision_drift(tmp_path: Path) -> None:
    value = build(tmp_path)
    value["evidence"][0]["sha256"] = "a" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        MODULE.validate_manifest(value, tmp_path)
    value = build(tmp_path)
    value["evidence"][0]["path"] = "../record.json"
    with pytest.raises(ValueError, match="unsafe"):
        MODULE.validate_structure(value)
    value = build(tmp_path)
    value["evidence"][0]["required_decision"] = "GO"
    with pytest.raises(ValueError, match="decision mismatch"):
        MODULE.validate_manifest(value, tmp_path)


def test_go_requires_every_bound_record_to_require_go(tmp_path: Path) -> None:
    value = build(tmp_path)
    value["decision"] = "GO"
    with pytest.raises(ValueError, match="GO requires every evidence record"):
        MODULE.validate_structure(value)
