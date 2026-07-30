from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_witness_ledger_checkpoint.py"
SPEC = spec_from_file_location("validate_public_operations_witness_ledger_checkpoint", SCRIPT)
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
        "schema": "lionsforge.public-operations-checkpoint-ledger-witness-ledger",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entries": [{"entry_digest": terminal}],
    }
    source_sha = write_json(tmp_path / "witness-ledger.json", ledger)
    return {
        "schema": "lionsforge.public-operations.witness-ledger-checkpoint",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "checkpoint_state": "VALID-NO-GO",
        "witness_ledger_path": "witness-ledger.json",
        "witness_ledger_sha256": source_sha,
        "witness_ledger_digest": MODULE.canonical_digest(ledger),
        "entry_count": 1,
        "terminal_entry_digest": terminal,
        "checkpoint_sequence": 1,
        "previous_checkpoint_digest": "0" * 64,
        "signer_role": "independent-witness-ledger-checkpoint-signer",
        "signer_key_id": "witness-checkpoint-key-0001",
        "signature_algorithm": "ed25519-sha256",
        "signature_sha256": "c" * 64,
        "nonce_sha256": "d" * 64,
        "issued_at": "2026-07-30T09:00:00Z",
        "expires_at": "2026-08-06T09:00:00Z",
    }


def validate(checkpoint: dict[str, object], tmp_path: Path) -> dict[str, object]:
    return MODULE.validate(
        checkpoint,
        tmp_path,
        "a" * 40,
        now=datetime(2026, 7, 30, 10, tzinfo=timezone.utc),
    )


def test_valid_checkpoint_is_non_authorizing(tmp_path: Path) -> None:
    result = validate(build(tmp_path), tmp_path)
    assert result["checkpoint_state"] == "VALID-NO-GO"
    assert result["authorization"] == "NONE"
    assert result["checkpoint_sequence"] == 1
    assert len(result["checkpoint_digest"]) == 64


def test_rejects_source_and_terminal_drift(tmp_path: Path) -> None:
    checkpoint = build(tmp_path)
    checkpoint["witness_ledger_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="byte drift"):
        validate(checkpoint, tmp_path)
    checkpoint = build(tmp_path)
    checkpoint["terminal_entry_digest"] = "e" * 64
    with pytest.raises(ValueError, match="terminal entry digest drift"):
        validate(checkpoint, tmp_path)


def test_rejects_candidate_and_state_drift(tmp_path: Path) -> None:
    checkpoint = build(tmp_path)
    checkpoint["candidate_sha"] = "e" * 40
    with pytest.raises(ValueError, match="witness ledger candidate drift"):
        MODULE.validate(checkpoint, tmp_path)
    checkpoint = build(tmp_path)
    checkpoint["checkpoint_state"] = "GO"
    with pytest.raises(ValueError, match="preserve NO-GO"):
        validate(checkpoint, tmp_path)


def test_rejects_sequence_and_duplicate_identity_material(tmp_path: Path) -> None:
    checkpoint = build(tmp_path)
    checkpoint["checkpoint_sequence"] = 2
    with pytest.raises(ValueError, match="requires previous digest"):
        validate(checkpoint, tmp_path)
    checkpoint = build(tmp_path)
    checkpoint["nonce_sha256"] = checkpoint["signature_sha256"]
    with pytest.raises(ValueError, match="duplicate identity material"):
        validate(checkpoint, tmp_path)


def test_rejects_future_expired_and_excessive_validity(tmp_path: Path) -> None:
    checkpoint = build(tmp_path)
    with pytest.raises(ValueError, match="future checkpoint issuance"):
        MODULE.validate(checkpoint, tmp_path, now=datetime(2026, 7, 30, 8, tzinfo=timezone.utc))
    checkpoint = build(tmp_path)
    with pytest.raises(ValueError, match="expired checkpoint"):
        MODULE.validate(checkpoint, tmp_path, now=datetime(2026, 8, 7, tzinfo=timezone.utc))
    checkpoint = build(tmp_path)
    checkpoint["expires_at"] = "2026-09-15T09:00:00Z"
    with pytest.raises(ValueError, match="excessive checkpoint validity"):
        validate(checkpoint, tmp_path)
