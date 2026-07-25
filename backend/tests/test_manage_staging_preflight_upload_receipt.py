import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "manage_staging_preflight_upload_receipt.py"
SPEC = spec_from_file_location("manage_staging_preflight_upload_receipt", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_report(path: Path, *, candidate: str = "a" * 40) -> None:
    payload = {
        "configuration": {},
        "provenance": {
            "candidate_sha": candidate,
            "generated_at": "2026-07-25T03:30:00Z",
            "repository": "brandonpapasan-coder/LionsForge-ai",
            "skip_endpoints": False,
            "workflow_run_attempt": 1,
            "workflow_run_id": 12345,
            "workflow_run_url": "https://github.com/brandonpapasan-coder/LionsForge-ai/actions/runs/12345",
        },
        "schema_version": 1,
        "status": "passed",
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def build(path: Path, **overrides):
    values = {
        "report": path,
        "artifact_name": "staging-preflight-" + "a" * 40,
        "artifact_id": 6789,
        "artifact_url": "https://github.com/brandonpapasan-coder/LionsForge-ai/actions/runs/12345/artifacts/6789",
        "artifact_digest": "sha256:" + "b" * 64,
    }
    values.update(overrides)
    return MODULE.build_receipt(**values)


def test_build_write_and_verify_receipt(tmp_path):
    report = tmp_path / "report.json"
    receipt = tmp_path / "receipt.json"
    write_report(report)
    expected = build(report)
    MODULE.write_receipt(receipt, expected)
    MODULE.verify_receipt(receipt, expected)
    assert expected["candidate"]["candidate_sha"] == "a" * 40
    assert expected["preflight"]["size_bytes"] == report.stat().st_size


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact_name", "staging-preflight-main"),
        ("artifact_id", 0),
        ("artifact_url", "https://github.com/other/repo/actions/runs/12345/artifacts/6789"),
        ("artifact_digest", "latest"),
    ],
)
def test_rejects_invalid_artifact_identity(tmp_path, field, value):
    report = tmp_path / "report.json"
    write_report(report)
    with pytest.raises(ValueError):
        build(report, **{field: value})


def test_rejects_weakened_or_tampered_sources(tmp_path):
    report = tmp_path / "report.json"
    write_report(report)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["status"] = "pending"
    report.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        build(report)


def test_rejects_symlinked_report_and_source_alias(tmp_path):
    source = tmp_path / "source.json"
    alias = tmp_path / "alias.json"
    write_report(source)
    alias.symlink_to(source)
    with pytest.raises(ValueError):
        build(alias)
    with pytest.raises(ValueError):
        MODULE.validate_output_path(output=source, report=source)


def test_verify_detects_receipt_mutation(tmp_path):
    report = tmp_path / "report.json"
    receipt = tmp_path / "receipt.json"
    write_report(report)
    expected = build(report)
    MODULE.write_receipt(receipt, expected)
    actual = json.loads(receipt.read_text(encoding="utf-8"))
    actual["artifact"]["id"] = 9999
    receipt.write_text(json.dumps(actual), encoding="utf-8")
    with pytest.raises(ValueError):
        MODULE.verify_receipt(receipt, expected)
