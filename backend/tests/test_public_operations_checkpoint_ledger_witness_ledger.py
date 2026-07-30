from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_checkpoint_ledger_witness_ledger.py"
SPEC = spec_from_file_location("validate_public_operations_checkpoint_ledger_witness_ledger", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: object) -> str:
    raw = json.dumps(value, sort_keys=True).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def build(tmp_path: Path, count: int = 2) -> dict[str, object]:
    candidate = "a" * 40
    entries = []
    previous = "0" * 64
    for sequence in range(1, count + 1):
        source = {
            "schema": "lionsforge.public-operations-checkpoint-ledger-witness",
            "schema_version": 1,
            "candidate_sha": candidate,
            "decision": "NO-GO",
            "witness_state": "VALID-NO-GO",
            "checkpoint_ledger_path": "checkpoint-ledger.json",
            "checkpoint_ledger_sha256": "1" * 64,
            "checkpoint_ledger_digest": f"{sequence + 1:x}" * 64,
            "entry_count": sequence,
            "terminal_entry_digest": f"{sequence + 3:x}" * 64,
            "witness_receipt_id": f"witness-receipt-{sequence:04d}",
            "witness_role": "independent-checkpoint-ledger-witness",
            "witness_key_id": "witness-key-0001",
            "signature_algorithm": "ed25519-sha256",
            "signature_sha256": f"{sequence + 5:x}" * 64,
            "nonce_sha256": f"{sequence + 7:x}" * 64,
            "issued_at": f"2026-07-29T{sequence:02d}:00:00Z",
            "expires_at": f"2026-08-05T{sequence:02d}:00:00Z",
        }
        path = tmp_path / f"witness-{sequence}.json"
        source_sha = write_json(path, source)
        material = {
            "sequence": sequence,
            "witness_path": path.name,
            "witness_sha256": source_sha,
            "witness_digest": MODULE.canonical_digest(source),
            "checkpoint_ledger_digest": source["checkpoint_ledger_digest"],
            "entry_count": source["entry_count"],
            "terminal_entry_digest": source["terminal_entry_digest"],
            "witness_receipt_id": source["witness_receipt_id"],
            "witness_role": source["witness_role"],
            "witness_key_id": source["witness_key_id"],
            "signature_algorithm": source["signature_algorithm"],
            "signature_sha256": source["signature_sha256"],
            "nonce_sha256": source["nonce_sha256"],
            "issued_at": source["issued_at"],
            "expires_at": source["expires_at"],
            "previous_entry_digest": previous,
        }
        digest = MODULE.canonical_digest(material)
        entries.append({**material, "entry_digest": digest})
        previous = digest
    return {
        "schema": "lionsforge.public-operations-checkpoint-ledger-witness-ledger",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entries": entries,
    }


def validate(ledger: dict[str, object], tmp_path: Path) -> dict[str, object]:
    return MODULE.validate(
        ledger,
        tmp_path,
        "a" * 40,
        now=datetime(2026, 7, 29, 3, tzinfo=timezone.utc),
    )


def test_valid_witness_ledger_is_non_authorizing(tmp_path: Path) -> None:
    result = validate(build(tmp_path), tmp_path)
    assert result["ledger_state"] == "VALID-NO-GO"
    assert result["authorization"] == "NONE"
    assert result["entry_count"] == 2
    assert len(result["witness_ledger_digest"]) == 64


def test_rejects_sequence_gap_and_broken_link(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][1]["sequence"] = 3
    with pytest.raises(ValueError, match="sequence gap"):
        validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][1]["previous_entry_digest"] = "f" * 64
    with pytest.raises(ValueError, match="broken previous-entry"):
        validate(ledger, tmp_path)


def test_rejects_duplicate_receipt_nonce_and_path(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][1]["witness_receipt_id"] = ledger["entries"][0]["witness_receipt_id"]
    with pytest.raises(ValueError, match="witness_receipt_id drift"):
        validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][1]["nonce_sha256"] = ledger["entries"][0]["nonce_sha256"]
    with pytest.raises(ValueError, match="nonce_sha256 drift"):
        validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][1]["witness_path"] = ledger["entries"][0]["witness_path"]
    with pytest.raises(ValueError, match="duplicate witness path"):
        validate(ledger, tmp_path)


def test_rejects_source_byte_and_identity_drift(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][0]["witness_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="source byte drift"):
        validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][1]["witness_key_id"] = "witness-key-0002"
    source_path = tmp_path / "witness-2.json"
    source = json.loads(source_path.read_text())
    source["witness_key_id"] = "witness-key-0002"
    ledger["entries"][1]["witness_sha256"] = write_json(source_path, source)
    ledger["entries"][1]["witness_digest"] = MODULE.canonical_digest(source)
    material = {name: ledger["entries"][1][name] for name in MODULE.ENTRY - {"entry_digest"}}
    ledger["entries"][1]["entry_digest"] = MODULE.canonical_digest(material)
    with pytest.raises(ValueError, match="witness identity drift"):
        validate(ledger, tmp_path)


def test_rejects_expired_receipt(tmp_path: Path) -> None:
    ledger = build(tmp_path, count=1)
    with pytest.raises(ValueError, match="expired or invalid"):
        MODULE.validate(
            ledger,
            tmp_path,
            now=datetime(2026, 8, 6, tzinfo=timezone.utc),
        )
