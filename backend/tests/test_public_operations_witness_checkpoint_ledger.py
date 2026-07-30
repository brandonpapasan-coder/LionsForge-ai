from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_witness_checkpoint_ledger.py"
SPEC = spec_from_file_location("validate_public_operations_witness_checkpoint_ledger", SCRIPT)
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
    checkpoint = {
        "schema": "lionsforge.public-operations.witness-ledger-checkpoint",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "checkpoint_state": "VALID-NO-GO",
        "issued_at": "2026-07-30T09:00:00Z",
        "expires_at": "2026-08-06T09:00:00Z",
    }
    source_sha = write_json(tmp_path / "checkpoint.json", checkpoint)
    checkpoint_digest = MODULE.canonical_digest(checkpoint)
    entry = {
        "sequence": 1,
        "checkpoint_path": "checkpoint.json",
        "checkpoint_sha256": source_sha,
        "checkpoint_digest": checkpoint_digest,
        "issued_at": checkpoint["issued_at"],
        "previous_entry_digest": "0" * 64,
    }
    entry["entry_digest"] = MODULE.canonical_digest(entry)
    return {
        "schema": "lionsforge.public-operations.witness-checkpoint-ledger",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entries": [entry],
    }


def validate(value: dict[str, object], tmp_path: Path) -> dict[str, object]:
    return MODULE.validate(
        value,
        tmp_path,
        "a" * 40,
        now=datetime(2026, 7, 30, 10, tzinfo=timezone.utc),
    )


def test_valid_ledger_is_non_authorizing(tmp_path: Path) -> None:
    result = validate(build(tmp_path), tmp_path)
    assert result["ledger_state"] == "VALID-NO-GO"
    assert result["authorization"] == "NONE"
    assert result["entry_count"] == 1
    assert len(result["terminal_entry_digest"]) == 64


def test_rejects_source_and_checkpoint_drift(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][0]["checkpoint_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="byte drift"):
        validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][0]["checkpoint_digest"] = "e" * 64
    with pytest.raises(ValueError, match="checkpoint digest drift"):
        validate(ledger, tmp_path)


def test_rejects_sequence_and_link_drift(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][0]["sequence"] = 2
    with pytest.raises(ValueError, match="sequence gap"):
        validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][0]["previous_entry_digest"] = "e" * 64
    with pytest.raises(ValueError, match="broken previous-entry link"):
        validate(ledger, tmp_path)


def test_rejects_expired_and_candidate_drift(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    with pytest.raises(ValueError, match="expired checkpoint"):
        MODULE.validate(ledger, tmp_path, now=datetime(2026, 8, 7, tzinfo=timezone.utc))
    ledger = build(tmp_path)
    ledger["candidate_sha"] = "e" * 40
    with pytest.raises(ValueError, match="checkpoint candidate drift"):
        MODULE.validate(ledger, tmp_path)
