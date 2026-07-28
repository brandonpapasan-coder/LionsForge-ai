from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from tests.test_public_operations_activation_validator import valid_record

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "manage_public_operations_activation_receipt.py"
)
SPEC = spec_from_file_location("manage_public_operations_activation_receipt", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CANDIDATE = "a" * 40
NOW = datetime(2026, 7, 28, 22, 45, tzinfo=timezone.utc)
build_receipt = MODULE.build_receipt
canonical_json = MODULE.canonical_json
canonical_record = MODULE.canonical_record
sha256_text = MODULE.sha256_text
validate_receipt = MODULE.validate_receipt


def receipt(record: str | None = None):
    return build_receipt(
        record_text=record or valid_record(),
        candidate_sha=CANDIDATE,
        generated_at=NOW,
    )


def test_receipt_is_deterministic_and_source_bound() -> None:
    first = receipt()
    second = receipt(valid_record() + "\n\n")

    assert first == second
    assert first["candidate_sha"] == CANDIDATE
    assert first["decision"] == "GO"
    assert first["record_sha256"] == sha256_text(canonical_record(valid_record()))
    assert first["record_bytes"] == len(canonical_record(valid_record()).encode("utf-8"))
    assert validate_receipt(first, record_text=valid_record(), expected_candidate_sha=CANDIDATE) == []


def test_receipt_rejects_unvalidated_or_sensitive_source() -> None:
    with pytest.raises(ValueError, match="not receipt-ready"):
        receipt(valid_record(decision="NO-GO"))

    with pytest.raises(ValueError, match="sensitive-field"):
        receipt(valid_record() + "\n- API key: must-not-exist")


def test_receipt_detects_source_tampering_and_candidate_substitution() -> None:
    value = receipt()
    changed_record = valid_record().replace("2 business days", "3 business days")
    findings = validate_receipt(
        value,
        record_text=changed_record,
        expected_candidate_sha="b" * 40,
    )

    assert "candidate SHA mismatch" in findings
    assert "source record digest mismatch" in findings
    assert "source record byte length mismatch" not in findings


def test_receipt_detects_metadata_tampering() -> None:
    mutations = (
        ("schema", "other", "unsupported receipt schema or version"),
        ("generator_version", "9.9.9", "unsupported generator version"),
        ("decision", "NO-GO", "receipt decision must be GO"),
        ("record_sha256", "bad", "record_sha256 must be 64 lowercase hexadecimal characters"),
        ("record_bytes", 0, "record_bytes must be a positive integer"),
        ("generated_at", "2026-07-28", "generated_at must be a valid UTC timestamp ending in Z"),
    )
    original = receipt()
    for field, replacement, expected in mutations:
        changed = deepcopy(original)
        changed[field] = replacement
        assert expected in validate_receipt(changed)


def test_receipt_rejects_extra_fields() -> None:
    value = receipt()
    value["private_content"] = "not allowed"
    assert "unexpected receipt field: private_content" in validate_receipt(value)


def test_cli_generate_and_validate(tmp_path: Path) -> None:
    record_path = tmp_path / "activation.md"
    receipt_path = tmp_path / "receipt.json"
    record_path.write_text(valid_record(), encoding="utf-8")

    generated = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "generate",
            str(record_path),
            "--candidate-sha",
            CANDIDATE,
            "--generated-at",
            "2026-07-28T22:45:00Z",
            "--output",
            str(receipt_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0
    assert json.loads(generated.stdout)["valid"] is True

    validated = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "validate",
            str(receipt_path),
            "--record",
            str(record_path),
            "--expected-candidate-sha",
            CANDIDATE,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert validated.returncode == 0
    assert json.loads(validated.stdout) == {"findings": [], "valid": True}

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "b" * 40
    receipt_path.write_text(canonical_json(payload), encoding="utf-8")
    rejected = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "validate",
            str(receipt_path),
            "--record",
            str(record_path),
            "--expected-candidate-sha",
            CANDIDATE,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert rejected.returncode == 1
    assert "candidate SHA mismatch" in json.loads(rejected.stdout)["findings"]
