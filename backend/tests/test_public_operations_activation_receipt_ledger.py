from __future__ import annotations

import hashlib
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_activation_receipt_ledger.py"
SPEC = spec_from_file_location("validate_public_operations_activation_receipt_ledger", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_empty_ledger_is_valid(tmp_path: Path) -> None:
    value = {
        "schema": "lionsforge.public-operations-activation-receipt-ledger",
        "schema_version": 1,
        "entries": [],
        "ledger_digest": hashlib.sha256(b"[]").hexdigest(),
    }
    result = MODULE.validate_ledger(value, tmp_path)
    assert result["result"] == "VALID"
    assert result["entry_count"] == 0


def build_entry(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    receipt = {
        "receipt_id": "receipt-00000001",
        "candidate_sha": "0" * 40,
        "decision": "NO-GO",
        "activation_mode": "NONE",
        "authorization_digest": "1" * 64,
        "issued_at": "2026-07-29T00:00:00Z",
    }
    raw = json.dumps(receipt, sort_keys=True).encode()
    (tmp_path / "receipt.json").write_bytes(raw)
    entry = {
        "sequence": 1,
        "receipt_id": receipt["receipt_id"],
        "candidate_sha": receipt["candidate_sha"],
        "decision": receipt["decision"],
        "activation_mode": receipt["activation_mode"],
        "receipt_path": "receipt.json",
        "receipt_sha256": hashlib.sha256(raw).hexdigest(),
        "authorization_digest": receipt["authorization_digest"],
        "issued_at": receipt["issued_at"],
        "previous_entry_digest": "0" * 64,
        "entry_digest": "",
    }
    entry["entry_digest"] = MODULE._entry_digest(entry)
    ledger = {
        "schema": "lionsforge.public-operations-activation-receipt-ledger",
        "schema_version": 1,
        "entries": [entry],
        "ledger_digest": MODULE._ledger_digest([entry]),
    }
    return ledger, entry


def test_valid_single_entry_ledger(tmp_path: Path) -> None:
    ledger, _ = build_entry(tmp_path)
    assert MODULE.validate_ledger(ledger, tmp_path)["entry_count"] == 1


def test_rejects_broken_chain_duplicate_and_receipt_drift(tmp_path: Path) -> None:
    ledger, entry = build_entry(tmp_path)
    entry["previous_entry_digest"] = "2" * 64
    with pytest.raises(ValueError, match="chain is broken"):
        MODULE.validate_ledger(ledger, tmp_path)
    ledger, entry = build_entry(tmp_path)
    duplicate = dict(entry)
    duplicate["sequence"] = 2
    ledger["entries"] = [entry, duplicate]
    ledger["ledger_digest"] = MODULE._ledger_digest(ledger["entries"])
    with pytest.raises(ValueError, match="duplicated"):
        MODULE.validate_ledger(ledger, tmp_path)
    ledger, _ = build_entry(tmp_path)
    (tmp_path / "receipt.json").write_text("{}")
    with pytest.raises(ValueError, match="receipt digest mismatch"):
        MODULE.validate_ledger(ledger, tmp_path)
