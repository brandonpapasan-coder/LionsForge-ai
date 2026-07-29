from __future__ import annotations

import hashlib
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_checkpoint_ledger.py"
SPEC = spec_from_file_location("validate_public_operations_checkpoint_ledger", SCRIPT)
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
            "candidate_sha": candidate,
            "decision": "NO-GO",
            "checkpoint_state": "VALID-NO-GO",
            "checkpoint_sequence": sequence,
            "checkpoint_digest": f"{sequence + 1:x}" * 64,
            "ledger_digest": f"{sequence + 3:x}" * 64,
            "entry_count": sequence,
            "terminal_entry_digest": f"{sequence + 5:x}" * 64,
            "signer_role": "independent-checkpoint-signer",
            "key_id": "checkpoint-key-0001",
            "signature_algorithm": "ed25519-sha256",
            "signature_sha256": f"{sequence + 7:x}" * 64,
            "issued_at": f"2026-07-29T{sequence:02d}:00:00Z",
        }
        path = tmp_path / f"checkpoint-{sequence}.json"
        source_sha = write_json(path, source)
        material = {
            "checkpoint_sequence": sequence,
            "checkpoint_path": path.name,
            "checkpoint_sha256": source_sha,
            "checkpoint_digest": source["checkpoint_digest"],
            "ledger_digest": source["ledger_digest"],
            "entry_count": source["entry_count"],
            "terminal_entry_digest": source["terminal_entry_digest"],
            "signer_role": source["signer_role"],
            "key_id": source["key_id"],
            "signature_algorithm": source["signature_algorithm"],
            "signature_sha256": source["signature_sha256"],
            "issued_at": source["issued_at"],
            "previous_entry_digest": previous,
        }
        entry_digest = MODULE.canonical_digest(material)
        entries.append({**material, "entry_digest": entry_digest})
        previous = entry_digest
    return {
        "schema": "lionsforge.public-operations-checkpoint-ledger",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entries": entries,
    }


def test_valid_checkpoint_ledger_is_non_authorizing(tmp_path: Path) -> None:
    result = MODULE.validate(build(tmp_path), tmp_path, "a" * 40)
    assert result["ledger_state"] == "VALID-NO-GO"
    assert result["authorization"] == "NONE"
    assert result["entry_count"] == 2
    assert len(result["checkpoint_ledger_digest"]) == 64


def test_rejects_sequence_gap_and_broken_link(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][1]["checkpoint_sequence"] = 3
    with pytest.raises(ValueError, match="sequence gap"):
        MODULE.validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][1]["previous_entry_digest"] = "f" * 64
    with pytest.raises(ValueError, match="broken previous-entry"):
        MODULE.validate(ledger, tmp_path)


def test_rejects_duplicate_checkpoint_and_path(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][1]["checkpoint_digest"] = ledger["entries"][0]["checkpoint_digest"]
    with pytest.raises(ValueError, match="duplicate checkpoint digest"):
        MODULE.validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][1]["checkpoint_path"] = ledger["entries"][0]["checkpoint_path"]
    with pytest.raises(ValueError, match="duplicate checkpoint path"):
        MODULE.validate(ledger, tmp_path)


def test_rejects_source_and_signer_drift(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][0]["ledger_digest"] = "e" * 64
    with pytest.raises(ValueError, match="ledger_digest drift"):
        MODULE.validate(ledger, tmp_path)
    ledger = build(tmp_path)
    ledger["entries"][1]["key_id"] = "checkpoint-key-0002"
    source_path = tmp_path / "checkpoint-2.json"
    source = json.loads(source_path.read_text())
    source["key_id"] = "checkpoint-key-0002"
    ledger["entries"][1]["checkpoint_sha256"] = write_json(source_path, source)
    material = {name: ledger["entries"][1][name] for name in MODULE.ENTRY - {"entry_digest"}}
    ledger["entries"][1]["entry_digest"] = MODULE.canonical_digest(material)
    with pytest.raises(ValueError, match="signer/key/algorithm drift"):
        MODULE.validate(ledger, tmp_path)
