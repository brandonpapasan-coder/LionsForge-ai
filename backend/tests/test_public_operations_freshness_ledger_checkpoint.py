from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_freshness_ledger_checkpoint.py"
SPEC = spec_from_file_location("validate_public_operations_freshness_ledger_checkpoint", SCRIPT)
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
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "ledger_digest": "c" * 64,
        "entries": [{"entry_digest": terminal}],
    }
    ledger_sha = write_json(tmp_path / "ledger.json", ledger)
    return {
        "schema": "lionsforge.public-operations-freshness-ledger-checkpoint",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "checkpoint_state": "VALID-NO-GO",
        "ledger_path": "ledger.json",
        "ledger_sha256": ledger_sha,
        "ledger_digest": ledger["ledger_digest"],
        "entry_count": 1,
        "terminal_entry_digest": terminal,
        "checkpoint_sequence": 1,
        "previous_checkpoint_digest": "0" * 64,
        "signer_role": "independent-checkpoint-signer",
        "key_id": "checkpoint-key-0001",
        "signature_algorithm": "ed25519-sha256",
        "signature_sha256": "d" * 64,
        "issued_at": "2026-07-29T12:00:00Z",
    }


def test_valid_checkpoint_is_non_authorizing(tmp_path: Path) -> None:
    result = MODULE.validate(
        build(tmp_path),
        tmp_path,
        "a" * 40,
        now=datetime(2026, 7, 29, 13, tzinfo=timezone.utc),
    )
    assert result["checkpoint_state"] == "VALID-NO-GO"
    assert result["authorization"] == "NONE"
    assert len(result["checkpoint_digest"]) == 64


def test_rejects_sequence_rollback_and_broken_link(tmp_path: Path) -> None:
    checkpoint = build(tmp_path)
    checkpoint["checkpoint_sequence"] = 2
    checkpoint["previous_checkpoint_digest"] = "e" * 64
    with pytest.raises(ValueError, match="rollback"):
        MODULE.validate(checkpoint, tmp_path, minimum_sequence=2)
    with pytest.raises(ValueError, match="broken checkpoint link"):
        MODULE.validate(checkpoint, tmp_path, expected_previous="f" * 64)


def test_rejects_ledger_and_terminal_drift(tmp_path: Path) -> None:
    checkpoint = build(tmp_path)
    checkpoint["ledger_digest"] = "e" * 64
    with pytest.raises(ValueError, match="ledger digest drift"):
        MODULE.validate(checkpoint, tmp_path)
    checkpoint = build(tmp_path)
    checkpoint["terminal_entry_digest"] = "e" * 64
    with pytest.raises(ValueError, match="terminal entry digest drift"):
        MODULE.validate(checkpoint, tmp_path)


def test_rejects_future_time_algorithm_and_unknown_keys(tmp_path: Path) -> None:
    checkpoint = build(tmp_path)
    checkpoint["issued_at"] = "2026-07-30T00:00:00Z"
    with pytest.raises(ValueError, match="future"):
        MODULE.validate(checkpoint, tmp_path, now=datetime(2026, 7, 29, 13, tzinfo=timezone.utc))
    checkpoint = build(tmp_path)
    checkpoint["signature_algorithm"] = "rsa-sha1"
    with pytest.raises(ValueError, match="unsupported signature"):
        MODULE.validate(checkpoint, tmp_path)
    checkpoint = build(tmp_path)
    checkpoint["api_token"] = "forbidden"
    with pytest.raises(ValueError, match="top-level keys"):
        MODULE.validate(checkpoint, tmp_path)
