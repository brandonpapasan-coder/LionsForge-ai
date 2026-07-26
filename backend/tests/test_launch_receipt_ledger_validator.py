from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_launch_receipt_ledger.py"
spec = importlib.util.spec_from_file_location("validate_launch_receipt_ledger", SCRIPT)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)

D1 = "1" * 64
D2 = "2" * 64
SHA1 = "a" * 40
SHA2 = "b" * 40


def ledger() -> dict:
    return {
        "schema": validator.SCHEMA,
        "schema_version": validator.VERSION,
        "entries": [
            {
                "sequence": 1,
                "receipt_sha256": D1,
                "predecessor_sha256": "",
                "release_sha": SHA1,
                "recorded_at": "2026-08-01T12:00:00Z",
                "status": "superseded",
                "reason": "New validated candidate",
                "owner": "release-owner",
            },
            {
                "sequence": 2,
                "receipt_sha256": D2,
                "predecessor_sha256": D1,
                "release_sha": SHA2,
                "recorded_at": "2026-08-02T12:00:00Z",
                "status": "current",
                "reason": "",
                "owner": "release-owner",
            },
        ],
    }


def test_valid_ledger_has_no_findings():
    assert validator.validate_ledger(ledger()) == []


def test_rejects_replay_fork_sequence_gap_and_duplicate_release():
    data = ledger()
    second = data["entries"][1]
    second["sequence"] = 3
    second["receipt_sha256"] = D1
    second["predecessor_sha256"] = "f" * 64
    second["release_sha"] = SHA1
    codes = {finding.code for finding in validator.validate_ledger(data)}
    assert {"sequence-gap", "replayed-receipt", "fork-or-gap", "duplicate-release"} <= codes


def test_rejects_timestamp_regression_and_invalid_current_rules():
    data = ledger()
    data["entries"][0]["status"] = "current"
    data["entries"][0]["reason"] = "unexpected"
    data["entries"][1]["status"] = "revoked"
    data["entries"][1]["reason"] = ""
    data["entries"][1]["recorded_at"] = "2026-07-31T12:00:00Z"
    codes = {finding.code for finding in validator.validate_ledger(data)}
    assert {
        "stale-current",
        "unexpected-reason",
        "final-not-current",
        "missing-reason",
        "timestamp-regression",
    } <= codes


def test_requires_exactly_one_current_entry():
    data = ledger()
    data["entries"][1]["status"] = "superseded"
    data["entries"][1]["reason"] = "retired"
    assert any(f.code == "current-count" for f in validator.validate_ledger(data))


def test_rejects_schema_shape_and_entry_fields():
    data = ledger()
    data["schema"] = "wrong"
    data["schema_version"] = 2
    data["extra"] = True
    del data["entries"][0]["owner"]
    data["entries"][0]["extra"] = True
    codes = {finding.code for finding in validator.validate_ledger(data)}
    assert {
        "unsupported-schema",
        "unsupported-version",
        "unsupported-field",
        "missing-entry-field",
        "unsupported-entry-field",
        "missing-owner",
    } <= codes


def test_validates_receipt_digest_and_release_identity(tmp_path: Path):
    receipt1 = tmp_path / "r1.json"
    receipt2 = tmp_path / "r2.json"
    receipt1.write_text(json.dumps({"identity": {"release_sha": SHA1}}), encoding="utf-8")
    receipt2.write_text(json.dumps({"identity": {"release_sha": SHA2}}), encoding="utf-8")
    data = ledger()
    data["entries"][0]["receipt_sha256"] = hashlib.sha256(receipt1.read_bytes()).hexdigest()
    data["entries"][1]["receipt_sha256"] = hashlib.sha256(receipt2.read_bytes()).hexdigest()
    data["entries"][1]["predecessor_sha256"] = data["entries"][0]["receipt_sha256"]
    assert validator.validate_ledger(data, [receipt1, receipt2]) == []

    receipt2.write_text(json.dumps({"identity": {"release_sha": "c" * 40}}), encoding="utf-8")
    codes = {finding.code for finding in validator.validate_ledger(data, [receipt1, receipt2])}
    assert {"receipt-drift", "release-drift"} <= codes


def test_rejects_receipt_count_mismatch(tmp_path: Path):
    receipt = tmp_path / "r.json"
    receipt.write_text("{}", encoding="utf-8")
    assert any(f.code == "receipt-count" for f in validator.validate_ledger(ledger(), [receipt]))


def test_privacy_scanner_detects_secret_and_prohibited_markers():
    findings = validator._privacy_findings(
        '"password": "super-secret"\n"note": "private tester identity"'
    )
    codes = {finding.code for finding in findings}
    assert {"sensitive-content", "prohibited-content"} <= codes


def test_findings_are_deterministic():
    data = ledger()
    data["entries"][1]["sequence"] = 9
    first = validator.validate_ledger(data)
    second = validator.validate_ledger(data)
    assert first == second
    assert first == sorted(first)


def test_cli_valid_and_malformed_json(tmp_path: Path):
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(ledger()), encoding="utf-8")
    valid = subprocess.run(
        [sys.executable, str(SCRIPT), str(ledger_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert valid.returncode == 0
    assert "VALID" in valid.stdout

    ledger_path.write_text("{not-json", encoding="utf-8")
    invalid = subprocess.run(
        [sys.executable, str(SCRIPT), str(ledger_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid.returncode == 1
    assert "malformed-json" in invalid.stdout
