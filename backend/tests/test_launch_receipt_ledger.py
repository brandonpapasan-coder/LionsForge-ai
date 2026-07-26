from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "launch_receipt_ledger.py"
spec = importlib.util.spec_from_file_location("launch_receipt_ledger", SCRIPT)
assert spec and spec.loader
ledger_tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ledger_tool
spec.loader.exec_module(ledger_tool)

D1 = "1" * 64
D2 = "2" * 64
SHA1 = "a" * 40
SHA2 = "b" * 40


def valid_ledger() -> dict:
    return {
        "schema": ledger_tool.SCHEMA,
        "schema_version": ledger_tool.VERSION,
        "validator_version": ledger_tool.TOOL_VERSION,
        "entries": [
            {
                "sequence": 1,
                "recorded_at": "2026-08-01T12:00:00Z",
                "receipt_sha256": D1,
                "predecessor_receipt_sha256": None,
                "release_identity": SHA1,
                "status": "superseded",
                "reason": "Replaced by a newer immutable candidate",
                "owner": "release-operations",
            },
            {
                "sequence": 2,
                "recorded_at": "2026-08-02T12:00:00Z",
                "receipt_sha256": D2,
                "predecessor_receipt_sha256": D1,
                "release_identity": SHA2,
                "status": "current",
                "reason": None,
                "owner": None,
            },
        ],
    }


def codes(findings) -> set[str]:
    return {finding.code for finding in findings}


def test_valid_ledger_is_accepted_and_findings_are_deterministic():
    ledger = valid_ledger()
    assert ledger_tool.validate_ledger(ledger) == []
    assert ledger_tool._canonical_json(ledger).endswith("\n")
    assert ledger_tool.validate_ledger(ledger) == ledger_tool.validate_ledger(ledger)


def test_rejects_schema_shape_and_extra_fields():
    ledger = valid_ledger()
    ledger["schema"] = "wrong"
    ledger["schema_version"] = 99
    ledger["validator_version"] = "0.0.0"
    ledger["extra"] = True
    del ledger["entries"][0]["owner"]
    ledger["entries"][1]["extra"] = True
    result = codes(ledger_tool.validate_ledger(ledger))
    assert {"unsupported-schema", "unsupported-version", "unsupported-validator", "unsupported-field", "missing-field"} <= result


def test_rejects_sequence_gaps_duplicates_and_timestamp_regression():
    ledger = valid_ledger()
    ledger["entries"][1]["sequence"] = 1
    ledger["entries"][1]["recorded_at"] = "2026-08-01T11:00:00Z"
    result = codes(ledger_tool.validate_ledger(ledger))
    assert {"duplicate-sequence", "sequence-gap", "timestamp-regression"} <= result


def test_rejects_replay_duplicate_identity_and_bad_digests():
    ledger = valid_ledger()
    ledger["entries"][1]["receipt_sha256"] = D1
    ledger["entries"][1]["release_identity"] = SHA1
    result = codes(ledger_tool.validate_ledger(ledger))
    assert {"replayed-receipt", "duplicate-release-identity"} <= result

    ledger = valid_ledger()
    ledger["entries"][0]["receipt_sha256"] = "INVALID"
    ledger["entries"][0]["release_identity"] = "INVALID"
    result = codes(ledger_tool.validate_ledger(ledger))
    assert {"invalid-digest", "invalid-release-identity"} <= result


def test_rejects_forks_cycles_and_invalid_first_predecessor():
    ledger = valid_ledger()
    ledger["entries"][0]["predecessor_receipt_sha256"] = D2
    ledger["entries"][1]["predecessor_receipt_sha256"] = "3" * 64
    result = codes(ledger_tool.validate_ledger(ledger))
    assert {"invalid-predecessor", "fork-or-gap"} <= result

    ledger = valid_ledger()
    ledger["entries"][1]["predecessor_receipt_sha256"] = D2
    assert "cycle" in codes(ledger_tool.validate_ledger(ledger))


def test_enforces_exactly_one_final_current_entry():
    ledger = valid_ledger()
    ledger["entries"][0]["status"] = "current"
    result = codes(ledger_tool.validate_ledger(ledger))
    assert {"nonfinal-current", "current-count"} <= result

    ledger = valid_ledger()
    ledger["entries"][1]["status"] = "revoked"
    ledger["entries"][1]["reason"] = "Candidate retired"
    ledger["entries"][1]["owner"] = "release-operations"
    result = codes(ledger_tool.validate_ledger(ledger))
    assert {"final-not-current", "current-count"} <= result


def test_requires_reason_and_owner_for_noncurrent_entries():
    ledger = valid_ledger()
    ledger["entries"][0]["reason"] = " "
    ledger["entries"][0]["owner"] = ""
    result = codes(ledger_tool.validate_ledger(ledger))
    assert {"missing-reason", "missing-owner"} <= result


def test_rejects_apparent_secrets_and_prohibited_private_fields():
    ledger = valid_ledger()
    ledger["entries"][0]["reason"] = "api_key=do-not-store-this"
    ledger["entries"][1]["answer_key"] = "private"
    result = codes(ledger_tool.validate_ledger(ledger))
    assert {"apparent-secret", "prohibited-field", "unsupported-field"} <= result


def test_optional_receipt_file_digest_and_schema_validation(tmp_path: Path):
    receipt = {"schema": "lionsforge.launch-evidence-chain-receipt"}
    raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(raw)

    ledger = valid_ledger()
    ledger["entries"][1]["receipt_sha256"] = digest
    findings = ledger_tool.validate_ledger(ledger, {digest: receipt_path})
    assert not {"receipt-digest-mismatch", "receipt-schema-invalid"} & codes(findings)

    receipt_path.write_text('{"schema":"wrong"}\n', encoding="utf-8")
    result = codes(ledger_tool.validate_ledger(ledger, {digest: receipt_path}))
    assert {"receipt-digest-mismatch", "receipt-schema-invalid"} <= result


def test_rejects_unreferenced_and_malformed_receipt_mappings(tmp_path: Path):
    path = tmp_path / "receipt.json"
    path.write_text("{not-json", encoding="utf-8")
    ledger = valid_ledger()
    result = codes(ledger_tool.validate_ledger(ledger, {"3" * 64: path}))
    assert "unreferenced-receipt" in result

    result = codes(ledger_tool.validate_ledger(ledger, {D2: path}))
    assert "receipt-malformed" in result


def test_cli_valid_and_invalid_exit_behavior(tmp_path: Path):
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(ledger_tool._canonical_json(valid_ledger()), encoding="utf-8")
    valid = subprocess.run([sys.executable, str(SCRIPT), str(ledger_path)], check=False, capture_output=True, text=True)
    assert valid.returncode == 0
    assert "VALID: launch receipt ledger" in valid.stdout
    assert "does not authorize" in valid.stdout

    ledger_path.write_text("{not-json", encoding="utf-8")
    invalid = subprocess.run([sys.executable, str(SCRIPT), str(ledger_path)], check=False, capture_output=True, text=True)
    assert invalid.returncode == 1
    assert "malformed-json" in invalid.stdout


def test_cli_rejects_invalid_receipt_mapping(tmp_path: Path):
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(ledger_tool._canonical_json(valid_ledger()), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(ledger_path), "--receipt", "missing-separator"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "invalid-receipt-mapping" in result.stdout
