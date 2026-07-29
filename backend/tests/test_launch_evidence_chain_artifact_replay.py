from __future__ import annotations

import json
import sys
import zipfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_launch_evidence_chain_artifact_replay.py"
SPEC = spec_from_file_location("verify_launch_evidence_chain_artifact_replay", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CANDIDATE = "a" * 40
WORKFLOW_SHA = "b" * 40
DIGEST = "sha256:" + "c" * 64


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    primary = tmp_path / "primary"
    provenance = tmp_path / "provenance"
    primary.mkdir()
    provenance.mkdir()
    source = primary / "launch-evidence-chain-receipt.json"
    _write_json(source, {"schema": "lionsforge.launch-evidence-chain-receipt", "schema_version": 1, "result": "VALID"})
    (primary / "launch-evidence-chain-validation.txt").write_text("VALID\n", encoding="utf-8")
    upload = {
        "artifact": {
            "digest": DIGEST,
            "id": 456,
            "name": f"launch-evidence-chain-{CANDIDATE}",
            "url": "https://github.com/owner/repo/actions/runs/123/artifacts/456",
        },
        "authorization_scope": {
            "deployment_authorized": False,
            "general_availability_authorized": False,
            "payment_collection_authorized": False,
            "public_access_authorized": False,
            "repository_only": True,
        },
        "candidate": {"candidate_sha": CANDIDATE, "repository": "owner/repo"},
        "provenance": {
            "run_attempt": 2,
            "run_id": 123,
            "workflow_name": "Launch Evidence Chain Receipt",
            "workflow_sha": WORKFLOW_SHA,
        },
        "schema": "lionsforge.launch-evidence-chain-upload-receipt",
        "schema_version": 1,
        "source_receipt": {
            "path": "launch-evidence-chain-receipt.json",
            "sha256": MODULE._sha256(source),
            "size_bytes": source.stat().st_size,
        },
    }
    _write_json(provenance / "launch-evidence-chain-upload-receipt.json", upload)
    return primary, provenance


def test_verify_replay_binds_candidate_run_artifact_and_source(tmp_path: Path) -> None:
    primary, provenance = _fixture(tmp_path)
    result = MODULE.verify_replay(
        primary_dir=primary,
        provenance_dir=provenance,
        candidate_sha=CANDIDATE,
        repository="owner/repo",
        workflow_name="Launch Evidence Chain Receipt",
        workflow_sha=WORKFLOW_SHA,
        run_id=123,
        run_attempt=2,
        artifact_id=456,
        artifact_name=f"launch-evidence-chain-{CANDIDATE}",
        artifact_url="https://github.com/owner/repo/actions/runs/123/artifacts/456",
        artifact_digest=DIGEST,
    )
    assert result["result"] == "VALID"
    assert result["source_receipt_sha256"] == MODULE._sha256(primary / "launch-evidence-chain-receipt.json")
    assert result["authorization_scope"]["repository_only"] is True


def test_verify_replay_rejects_metadata_and_source_substitution(tmp_path: Path) -> None:
    primary, provenance = _fixture(tmp_path)
    with pytest.raises(ValueError, match="artifact URL"):
        MODULE.verify_replay(
            primary_dir=primary,
            provenance_dir=provenance,
            candidate_sha=CANDIDATE,
            repository="owner/repo",
            workflow_name="Launch Evidence Chain Receipt",
            workflow_sha=WORKFLOW_SHA,
            run_id=123,
            run_attempt=2,
            artifact_id=456,
            artifact_name=f"launch-evidence-chain-{CANDIDATE}",
            artifact_url="https://github.com/owner/repo/actions/runs/999/artifacts/456",
            artifact_digest=DIGEST,
        )
    (primary / "launch-evidence-chain-receipt.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source chain receipt"):
        MODULE.verify_replay(
            primary_dir=primary,
            provenance_dir=provenance,
            candidate_sha=CANDIDATE,
            repository="owner/repo",
            workflow_name="Launch Evidence Chain Receipt",
            workflow_sha=WORKFLOW_SHA,
            run_id=123,
            run_attempt=2,
            artifact_id=456,
            artifact_name=f"launch-evidence-chain-{CANDIDATE}",
            artifact_url="https://github.com/owner/repo/actions/runs/123/artifacts/456",
            artifact_digest=DIGEST,
        )


def test_safe_extract_rejects_traversal_and_unexpected_files(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../escape.json", "{}")
    with pytest.raises(ValueError, match="unsafe path"):
        MODULE.safe_extract(archive, tmp_path / "out", {"expected.json"})

    archive = tmp_path / "unexpected.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("unexpected.json", "{}")
    with pytest.raises(ValueError, match="expected contract"):
        MODULE.safe_extract(archive, tmp_path / "out2", {"expected.json"})
