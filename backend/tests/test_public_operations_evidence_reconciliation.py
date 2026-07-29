from __future__ import annotations

import hashlib
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_evidence_reconciliation.py"
SPEC = spec_from_file_location("validate_public_operations_evidence_reconciliation", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: object) -> str:
    raw = json.dumps(value, sort_keys=True).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def build(tmp_path: Path) -> dict[str, object]:
    candidate = "0" * 40
    aggregate = "1" * 64
    authorization = "2" * 64
    receipt_id = "receipt-00000001"

    manifest = {"candidate_sha": candidate}
    manifest_digest = write_json(tmp_path / "manifest.json", manifest)

    binding = {
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "activation_mode": "NONE",
        "aggregate_evidence_sha256": aggregate,
        "manifest_sha256": manifest_digest,
    }
    binding_digest = write_json(tmp_path / "binding.json", binding)

    receipt = {
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "activation_mode": "NONE",
        "aggregate_evidence_sha256": aggregate,
        "binding_sha256": binding_digest,
        "authorization_digest": authorization,
        "receipt_id": receipt_id,
    }
    receipt_digest = write_json(tmp_path / "receipt.json", receipt)

    ledger = {
        "entries": [
            {
                "receipt_id": receipt_id,
                "candidate_sha": candidate,
                "decision": "NO-GO",
                "activation_mode": "NONE",
                "receipt_sha256": receipt_digest,
                "authorization_digest": authorization,
            }
        ]
    }
    ledger_digest = write_json(tmp_path / "ledger.json", ledger)

    return {
        "schema": "lionsforge.public-operations-evidence-reconciliation",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "activation_mode": "NONE",
        "manifest_path": "manifest.json",
        "manifest_sha256": manifest_digest,
        "binding_path": "binding.json",
        "binding_sha256": binding_digest,
        "receipt_path": "receipt.json",
        "receipt_sha256": receipt_digest,
        "ledger_path": "ledger.json",
        "ledger_sha256": ledger_digest,
        "aggregate_evidence_sha256": aggregate,
        "authorization_digest": authorization,
        "receipt_id": receipt_id,
    }


def test_valid_no_go_chain(tmp_path: Path) -> None:
    result = MODULE.validate_reconciliation(build(tmp_path), tmp_path, "0" * 40)
    assert result["result"] == "VALID"
    assert result["decision"] == "NO-GO"
    assert len(result["reconciliation_digest"]) == 64


def test_rejects_candidate_and_binding_drift(tmp_path: Path) -> None:
    value = build(tmp_path)
    with pytest.raises(ValueError, match="expected candidate"):
        MODULE.validate_reconciliation(value, tmp_path, "a" * 40)

    binding = json.loads((tmp_path / "binding.json").read_text())
    binding["candidate_sha"] = "a" * 40
    value["binding_sha256"] = write_json(tmp_path / "binding.json", binding)
    with pytest.raises(ValueError, match="binding candidate mismatch"):
        MODULE.validate_reconciliation(value, tmp_path)


def test_rejects_missing_or_duplicate_ledger_receipt(tmp_path: Path) -> None:
    value = build(tmp_path)
    ledger = {"entries": []}
    value["ledger_sha256"] = write_json(tmp_path / "ledger.json", ledger)
    with pytest.raises(ValueError, match="exactly one"):
        MODULE.validate_reconciliation(value, tmp_path)

    value = build(tmp_path)
    ledger = json.loads((tmp_path / "ledger.json").read_text())
    ledger["entries"].append(dict(ledger["entries"][0]))
    value["ledger_sha256"] = write_json(tmp_path / "ledger.json", ledger)
    with pytest.raises(ValueError, match="exactly one"):
        MODULE.validate_reconciliation(value, tmp_path)


def test_rejects_digest_unsafe_path_and_secret_key(tmp_path: Path) -> None:
    value = build(tmp_path)
    value["receipt_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="receipt digest mismatch"):
        MODULE.validate_reconciliation(value, tmp_path)

    value = build(tmp_path)
    value["manifest_path"] = "../manifest.json"
    with pytest.raises(ValueError, match="unsafe"):
        MODULE.validate_reconciliation(value, tmp_path)

    value = build(tmp_path)
    value["api_token"] = "forbidden"
    with pytest.raises(ValueError, match="top-level keys"):
        MODULE.validate_reconciliation(value, tmp_path)
