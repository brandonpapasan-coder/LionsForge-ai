from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "manage_launch_evidence_chain_upload_receipt.py"
)
SPEC = spec_from_file_location("manage_launch_evidence_chain_upload_receipt", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CANDIDATE = "a" * 40
WORKFLOW_SHA = "b" * 40
ARTIFACT_DIGEST = "sha256:" + "c" * 64


def source_receipt(tmp_path: Path) -> Path:
    path = tmp_path / "launch-evidence-chain-receipt.json"
    path.write_text(
        json.dumps(
            {
                "schema": "lionsforge.launch-evidence-chain-receipt",
                "schema_version": 1,
                "result": "VALID",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def build(tmp_path: Path):
    source = source_receipt(tmp_path)
    return MODULE.build_receipt(
        source_receipt=source,
        candidate_sha=CANDIDATE,
        repository="owner/repo",
        workflow_name="Launch Evidence Chain Receipt",
        workflow_sha=WORKFLOW_SHA,
        run_id=123,
        run_attempt=2,
        artifact_id=456,
        artifact_name=f"launch-evidence-chain-{CANDIDATE}",
        artifact_url="https://github.com/owner/repo/actions/runs/123/artifacts/456",
        artifact_digest=ARTIFACT_DIGEST,
    )


def test_build_receipt_binds_source_candidate_run_and_artifact(tmp_path: Path) -> None:
    value = build(tmp_path)
    assert value["candidate"]["candidate_sha"] == CANDIDATE
    assert value["provenance"] == {
        "run_attempt": 2,
        "run_id": 123,
        "workflow_name": "Launch Evidence Chain Receipt",
        "workflow_sha": WORKFLOW_SHA,
    }
    assert value["artifact"]["digest"] == ARTIFACT_DIGEST
    assert value["authorization_scope"]["repository_only"] is True
    assert value["authorization_scope"]["public_access_authorized"] is False


def test_receipt_rejects_url_substitution_and_invalid_source(tmp_path: Path) -> None:
    source = source_receipt(tmp_path)
    with pytest.raises(ValueError, match="artifact URL"):
        MODULE.build_receipt(
            source_receipt=source,
            candidate_sha=CANDIDATE,
            repository="owner/repo",
            workflow_name="Launch Evidence Chain Receipt",
            workflow_sha=WORKFLOW_SHA,
            run_id=123,
            run_attempt=1,
            artifact_id=456,
            artifact_name=f"launch-evidence-chain-{CANDIDATE}",
            artifact_url="https://github.com/owner/repo/actions/runs/999/artifacts/456",
            artifact_digest=ARTIFACT_DIGEST,
        )
    source.write_text('{"schema":"other","schema_version":1,"result":"VALID"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="source receipt schema"):
        MODULE.build_receipt(
            source_receipt=source,
            candidate_sha=CANDIDATE,
            repository="owner/repo",
            workflow_name="Launch Evidence Chain Receipt",
            workflow_sha=WORKFLOW_SHA,
            run_id=123,
            run_attempt=2,
            artifact_id=456,
            artifact_name=f"launch-evidence-chain-{CANDIDATE}",
            artifact_url="https://github.com/owner/repo/actions/runs/123/artifacts/456",
            artifact_digest=ARTIFACT_DIGEST,
        )


def test_verify_detects_source_drift_and_receipt_tampering(tmp_path: Path) -> None:
    source = source_receipt(tmp_path)
    output = tmp_path / "upload-receipt.json"
    expected = build(tmp_path)
    MODULE.write_receipt(output, expected)
    MODULE.verify_receipt(output, expected)

    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    changed = MODULE.build_receipt(
        source_receipt=source,
        candidate_sha=CANDIDATE,
        repository="owner/repo",
        workflow_name="Launch Evidence Chain Receipt",
        workflow_sha=WORKFLOW_SHA,
        run_id=123,
        run_attempt=2,
        artifact_id=456,
        artifact_name=f"launch-evidence-chain-{CANDIDATE}",
        artifact_url="https://github.com/owner/repo/actions/runs/123/artifacts/456",
        artifact_digest=ARTIFACT_DIGEST,
    )
    with pytest.raises(ValueError, match="does not match"):
        MODULE.verify_receipt(output, changed)

    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["artifact"]["id"] = 999
    output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        MODULE.verify_receipt(output, expected)
