from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_activation_receipt.py"
SPEC = spec_from_file_location("validate_public_operations_activation_receipt_v2", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def build(tmp_path: Path, decision: str = "NO-GO") -> dict[str, object]:
    mode = "NONE" if decision == "NO-GO" else "CONTROLLED-BETA"
    aggregate = "1" * 64
    binding = {"candidate_sha": "0" * 40, "decision": decision, "activation_mode": mode, "aggregate_evidence_sha256": aggregate, "authorization_owner_role": "Public operations owner role"}
    raw = json.dumps(binding, sort_keys=True).encode()
    path = tmp_path / "binding.json"
    path.write_bytes(raw)
    value = {"schema": "lionsforge.public-operations-activation-receipt", "schema_version": 1, "candidate_sha": "0" * 40, "decision": decision, "activation_mode": mode, "binding_path": path.name, "binding_sha256": hashlib.sha256(raw).hexdigest(), "aggregate_evidence_sha256": aggregate, "receipt_id": "receipt-00000001", "issuer_role": "Independent receipt issuer role", "issued_at": "2026-07-29T00:00:00Z", "expires_at": "2026-07-30T00:00:00Z", "authorization_digest": ""}
    value["authorization_digest"] = MODULE._auth_digest(value["binding_sha256"], value["candidate_sha"], decision, mode, aggregate, value["receipt_id"], value["issuer_role"], value["issued_at"], value["expires_at"])
    return value


def test_valid_no_go_receipt(tmp_path: Path) -> None:
    result = MODULE.validate_record(build(tmp_path), tmp_path, "0" * 40, now=datetime(2026, 7, 29, 12, tzinfo=timezone.utc))
    assert result["result"] == "VALID"
    assert result["activation_mode"] == "NONE"


def test_rejects_digest_candidate_and_replay(tmp_path: Path) -> None:
    value = build(tmp_path)
    value["binding_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="binding digest mismatch"):
        MODULE.validate_record(value, tmp_path)
    with pytest.raises(ValueError, match="expected candidate"):
        MODULE.validate_record(build(tmp_path), tmp_path, "a" * 40)
    with pytest.raises(ValueError, match="already present"):
        MODULE.validate_record(build(tmp_path), tmp_path, ledger={"receipt-00000001"})


def test_rejects_mode_time_and_authorization_drift(tmp_path: Path) -> None:
    value = build(tmp_path)
    value["activation_mode"] = "CONTROLLED-BETA"
    with pytest.raises(ValueError, match="NO-GO requires"):
        MODULE.validate_record(value, tmp_path)
    value = build(tmp_path)
    value["authorization_digest"] = "a" * 64
    with pytest.raises(ValueError, match="authorization digest mismatch"):
        MODULE.validate_record(value, tmp_path)
    value = build(tmp_path)
    value["expires_at"] = value["issued_at"]
    with pytest.raises(ValueError, match="after issued_at"):
        MODULE.validate_record(value, tmp_path)