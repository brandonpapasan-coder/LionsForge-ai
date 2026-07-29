from __future__ import annotations

import hashlib
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_freshness_receipt_ledger.py"
SPEC = spec_from_file_location("validate_public_operations_freshness_receipt_ledger", SCRIPT)
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
    for index in range(1, count + 1):
        receipt = {
            "candidate_sha": candidate,
            "decision": "NO-GO",
            "receipt_state": "VALID-NO-GO",
            "receipt_id": f"freshness-receipt-{index:04d}",
            "nonce_sha256": f"{index:x}" * 64,
            "receipt_digest": f"{index + 2:x}" * 64,
            "issued_at": f"2026-07-29T{index:02d}:00:00Z",
        }
        path = tmp_path / f"receipt-{index}.json"
        source_sha = write_json(path, receipt)
        material = {
            "sequence": index,
            "receipt_path": path.name,
            "receipt_sha256": source_sha,
            "receipt_id": receipt["receipt_id"],
            "nonce_sha256": receipt["nonce_sha256"],
            "receipt_digest": receipt["receipt_digest"],
            "issued_at": receipt["issued_at"],
            "previous_entry_digest": previous,
        }
        digest = MODULE.canonical_digest(material)
        entries.append({**material, "entry_digest": digest})
        previous = digest
    return {
        "schema": "lionsforge.public-operations-freshness-receipt-ledger",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entries": entries,
    }


def test_valid_hash_chained_ledger(tmp_path: Path) -> None:
    result = MODULE.validate(build(tmp_path), tmp_path, "a" * 40)
    assert result["ledger_state"] == "VALID-NO-GO"
    assert result["entry_count"] == 2
    assert len(result["ledger_digest"]) == 64


def test_rejects_sequence_gap_and_broken_link(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][1]["sequence"] = 3
    with pytest.raises(ValueError, match="sequence gap"):
        MODULE.validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][1]["previous_entry_digest"] = "f" * 64
    with pytest.raises(ValueError, match="broken previous-entry"):
        MODULE.validate(ledger, tmp_path)


def test_rejects_duplicate_identity_material(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][1]["receipt_id"] = ledger["entries"][0]["receipt_id"]
    path = tmp_path / "receipt-2.json"
    source = json.loads(path.read_text())
    source["receipt_id"] = ledger["entries"][1]["receipt_id"]
    ledger["entries"][1]["receipt_sha256"] = write_json(path, source)
    material = {k: ledger["entries"][1][k] for k in MODULE.ENTRY - {"entry_digest"}}
    ledger["entries"][1]["entry_digest"] = MODULE.canonical_digest(material)
    with pytest.raises(ValueError, match="duplicate receipt identity"):
        MODULE.validate(ledger, tmp_path)


def test_rejects_source_drift_and_non_monotonic_time(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][0]["receipt_digest"] = "e" * 64
    with pytest.raises(ValueError, match="receipt_digest drift"):
        MODULE.validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][1]["issued_at"] = ledger["entries"][0]["issued_at"]
    with pytest.raises(ValueError, match="issued_at drift|increase monotonically"):
        MODULE.validate(ledger, tmp_path)
