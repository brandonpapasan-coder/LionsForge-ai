from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_checkpoint_ledger_witness.py"
SPEC = spec_from_file_location("validate_public_operations_checkpoint_ledger_witness", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: object) -> str:
    raw = json.dumps(value, sort_keys=True).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def build(tmp_path: Path) -> dict[str, object]:
    candidate = "a" * 40
    terminal = "b" * 64
    ledger = {
        "schema": "lionsforge.public-operations-checkpoint-ledger",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entries": [{"entry_digest": terminal}],
    }
    ledger_sha = write_json(tmp_path / "checkpoint-ledger.json", ledger)
    return {
        "schema": "lionsforge.public-operations-checkpoint-ledger-witness",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "witness_state": "VALID-NO-GO",
        "checkpoint_ledger_path": "checkpoint-ledger.json",
        "checkpoint_ledger_sha256": ledger_sha,
        "checkpoint_ledger_digest": MODULE.canonical_digest(ledger),
        "entry_count": 1,
        "terminal_entry_digest": terminal,
        "witness_receipt_id": "witness-receipt-0001",
        "witness_role": "independent-checkpoint-ledger-witness",
        "witness_key_id": "witness-key-0001",
        "signature_algorithm": "ed25519-sha256",
        "signature_sha256": "c" * 64,
        "nonce_sha256": "d" * 64,
        "issued_at": "2026-07-29T20:00:00Z",
        "expires_at": "2026-08-05T20:00:00Z",
    }


def test_valid_witness_is_non_authorizing(tmp_path: Path) -> None:
    result = MODULE.validate(
        build(tmp_path), tmp_path, "a" * 40,
        now=datetime(2026, 7, 29, 21, tzinfo=timezone.utc),
    )
    assert result["witness_state"] == "VALID-NO-GO"
    assert result["authorization"] == "NONE"
    assert len(result["witness_digest"]) == 64


def test_rejects_ledger_byte_and_terminal_drift(tmp_path: Path) -> None:
    witness = build(tmp_path)
    witness["checkpoint_ledger_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="byte drift"):
        MODULE.validate(witness, tmp_path)
    witness = build(tmp_path)
    witness["terminal_entry_digest"] = "e" * 64
    with pytest.raises(ValueError, match="terminal entry digest drift"):
        MODULE.validate(witness, tmp_path)


def test_rejects_candidate_and_state_drift(tmp_path: Path) -> None:
    witness = build(tmp_path)
    witness["candidate_sha"] = "e" * 40
    with pytest.raises(ValueError, match="checkpoint ledger candidate drift"):
        MODULE.validate(witness, tmp_path)
    witness = build(tmp_path)
    witness["witness_state"] = "GO"
    with pytest.raises(ValueError, match="preserve NO-GO"):
        MODULE.validate(witness, tmp_path)


def test_rejects_replay_material_and_unsupported_algorithm(tmp_path: Path) -> None:
    witness = build(tmp_path)
    witness["nonce_sha256"] = witness["signature_sha256"]
    with pytest.raises(ValueError, match="duplicate identity material"):
        MODULE.validate(witness, tmp_path)
    witness = build(tmp_path)
    witness["signature_algorithm"] = "rsa-sha1"
    with pytest.raises(ValueError, match="unsupported signature"):
        MODULE.validate(witness, tmp_path)


def test_rejects_future_expired_and_excessive_validity(tmp_path: Path) -> None:
    witness = build(tmp_path)
    with pytest.raises(ValueError, match="future witness issuance"):
        MODULE.validate(witness, tmp_path, now=datetime(2026, 7, 29, 19, tzinfo=timezone.utc))
    witness = build(tmp_path)
    with pytest.raises(ValueError, match="expired witness"):
        MODULE.validate(witness, tmp_path, now=datetime(2026, 8, 6, tzinfo=timezone.utc))
    witness = build(tmp_path)
    witness["expires_at"] = "2026-09-15T20:00:00Z"
    with pytest.raises(ValueError, match="excessive witness validity"):
        MODULE.validate(witness, tmp_path, now=datetime(2026, 7, 29, 21, tzinfo=timezone.utc))
