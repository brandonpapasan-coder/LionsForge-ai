from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "launch_evidence_chain_receipt.py"
spec = importlib.util.spec_from_file_location("launch_evidence_chain_receipt", SCRIPT)
assert spec and spec.loader
receipt_tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = receipt_tool
spec.loader.exec_module(receipt_tool)

SHA = "a" * 40
ROLLBACK = "b" * 40
BACKEND = "sha256:" + "c" * 64
FRONTEND = "sha256:" + "d" * 64


def records() -> dict[str, str]:
    return {
        "production": (
            f"- Release SHA: {SHA}\n"
            f"- Rollback SHA: {ROLLBACK}\n"
            f"- Backend image digest: {BACKEND}\n"
            f"- Frontend image digest: {FRONTEND}\n"
            "- Decision: GO\n"
        ),
        "public_operations": f"- Release candidate SHA: {SHA}\n- Decision: GO\n",
        "controlled_beta": (
            f"- Release SHA: {SHA}\n"
            f"- Previous rollback SHA: {ROLLBACK}\n"
            f"- Backend image digest: {BACKEND}\n"
            f"- Frontend image digest: {FRONTEND}\n"
            "- [x] GO — complete\n"
        ),
        "ga": (
            f"- Release SHA: {SHA}\n"
            f"- Previous rollback SHA: {ROLLBACK}\n"
            f"- Backend image digest: {BACKEND}\n"
            f"- Frontend image digest: {FRONTEND}\n"
            "- [x] GO — complete\n"
        ),
    }


def allow_chain(monkeypatch) -> None:
    monkeypatch.setattr(
        receipt_tool,
        "_load_chain_validator",
        lambda: SimpleNamespace(validate_chain=lambda _records: []),
    )


def test_build_receipt_is_canonical_and_binds_identity(monkeypatch):
    allow_chain(monkeypatch)
    generated_at = datetime(2026, 8, 1, 12, 30, 45, 999999, tzinfo=timezone.utc)
    receipt = receipt_tool.build_receipt(records(), generated_at)

    assert receipt["schema"] == receipt_tool.SCHEMA
    assert receipt["schema_version"] == 1
    assert receipt["validator_version"] == receipt_tool.TOOL_VERSION
    assert receipt["generated_at"] == "2026-08-01T12:30:45Z"
    assert receipt["result"] == "VALID"
    assert receipt["identity"] == {
        "release_sha": SHA,
        "rollback_sha": ROLLBACK,
        "backend_image_digest": BACKEND,
        "frontend_image_digest": FRONTEND,
        "ga_decision": "GO",
    }
    assert set(receipt["records"]) == set(receipt_tool.RECORD_KINDS)
    assert receipt_tool._canonical_json(receipt) == receipt_tool._canonical_json(receipt)
    assert receipt_tool._canonical_json(receipt).endswith("\n")


def test_generation_fails_when_chain_is_invalid(monkeypatch):
    finding = SimpleNamespace(record="production", code="identity-mismatch")
    monkeypatch.setattr(
        receipt_tool,
        "_load_chain_validator",
        lambda: SimpleNamespace(validate_chain=lambda _records: [finding]),
    )
    try:
        receipt_tool.build_receipt(records())
    except ValueError as exc:
        assert "production:identity-mismatch" in str(exc)
    else:
        raise AssertionError("invalid chain unexpectedly produced a receipt")


def test_generation_requires_timezone_aware_utc(monkeypatch):
    allow_chain(monkeypatch)
    try:
        receipt_tool.build_receipt(records(), datetime(2026, 8, 1, 12, 0, 0))
    except ValueError as exc:
        assert "timezone-aware UTC" in str(exc)
    else:
        raise AssertionError("naive timestamp unexpectedly accepted")


def test_valid_receipt_matches_source_records(monkeypatch):
    allow_chain(monkeypatch)
    receipt = receipt_tool.build_receipt(
        records(), datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    assert receipt_tool.validate_receipt(receipt, records()) == []


def test_detects_record_and_identity_drift(monkeypatch):
    allow_chain(monkeypatch)
    original = records()
    receipt = receipt_tool.build_receipt(
        original, datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    changed = records()
    changed["ga"] = changed["ga"].replace(SHA, "e" * 40)
    findings = receipt_tool.validate_receipt(receipt, changed)
    assert any(f.code == "record-drift" and "ga" in f.field for f in findings)
    assert any(f.code == "identity-drift" and "release_sha" in f.field for f in findings)


def test_rejects_swapped_record_bindings(monkeypatch):
    allow_chain(monkeypatch)
    source = records()
    receipt = receipt_tool.build_receipt(
        source, datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    receipt["records"]["production"], receipt["records"]["ga"] = (
        receipt["records"]["ga"],
        receipt["records"]["production"],
    )
    findings = receipt_tool.validate_receipt(receipt, source)
    assert sum(f.code == "record-drift" for f in findings) == 2


def test_rejects_schema_version_timestamp_and_shape_errors(monkeypatch):
    allow_chain(monkeypatch)
    receipt = receipt_tool.build_receipt(
        records(), datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    receipt["schema"] = "wrong"
    receipt["schema_version"] = 99
    receipt["validator_version"] = "0.0.0"
    receipt["generated_at"] = "2026-08-01T12:00:00"
    receipt["extra"] = True
    del receipt["result"]
    findings = receipt_tool.validate_receipt(receipt, records())
    codes = {finding.code for finding in findings}
    assert {
        "unsupported-schema",
        "unsupported-version",
        "unsupported-validator",
        "invalid-timestamp",
        "unsupported-field",
        "missing-field",
        "invalid-result",
    } <= codes


def test_rejects_invalid_record_and_identity_bindings(monkeypatch):
    allow_chain(monkeypatch)
    receipt = receipt_tool.build_receipt(
        records(), datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    receipt["records"]["production"] = {"sha256": "INVALID", "extra": "x"}
    receipt["identity"]["release_sha"] = "INVALID"
    receipt["identity"]["ga_decision"] = "CONDITIONAL GO"
    findings = receipt_tool.validate_receipt(receipt, records())
    assert any(f.code == "invalid-binding" for f in findings)
    assert any(f.code == "invalid-identity-value" and "release_sha" in f.field for f in findings)
    assert any(f.code == "invalid-identity-value" and "ga_decision" in f.field for f in findings)


def test_propagates_underlying_chain_findings(monkeypatch):
    finding = SimpleNamespace(record="ga", code="decision-order", message="upstream NO-GO")
    monkeypatch.setattr(
        receipt_tool,
        "_load_chain_validator",
        lambda: SimpleNamespace(validate_chain=lambda _records: [finding]),
    )
    receipt = {
        "schema": receipt_tool.SCHEMA,
        "schema_version": receipt_tool.VERSION,
        "validator_version": receipt_tool.TOOL_VERSION,
        "generated_at": "2026-08-01T12:00:00Z",
        "result": "VALID",
        "identity": receipt_tool._identity(records()),
        "records": {
            kind: {"sha256": receipt_tool._sha256_text(text)}
            for kind, text in records().items()
        },
    }
    findings = receipt_tool.validate_receipt(receipt, records())
    assert any(f.code == "chain-invalid" and f.field == "ga" for f in findings)


def test_findings_are_deterministic(monkeypatch):
    allow_chain(monkeypatch)
    receipt = {"schema": "wrong"}
    first = receipt_tool.validate_receipt(receipt, records())
    second = receipt_tool.validate_receipt(receipt, records())
    assert first == second
    assert first == sorted(first)


def test_cli_generate_and_validate(monkeypatch, tmp_path: Path):
    allow_chain(monkeypatch)
    source = records()
    paths = []
    for kind in receipt_tool.RECORD_KINDS:
        path = tmp_path / f"{kind}.md"
        path.write_text(source[kind], encoding="utf-8")
        paths.append(path)

    receipt = receipt_tool.build_receipt(
        source, datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(receipt_tool._canonical_json(receipt), encoding="utf-8")

    result = receipt_tool.main(["validate", *(str(path) for path in paths), str(receipt_path)])
    assert result == 0


def test_cli_rejects_malformed_json(tmp_path: Path):
    paths = []
    for kind in receipt_tool.RECORD_KINDS:
        path = tmp_path / f"{kind}.md"
        path.write_text("record", encoding="utf-8")
        paths.append(path)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text("{not-json", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", *(str(path) for path in paths), str(receipt_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "malformed-json" in result.stdout
