import json
from pathlib import Path

import pytest

from scripts.write_internal_alpha_authorization_manifest import build_manifest, write_atomic

SHA = "a" * 40
DIGEST_A = "sha256:" + "b" * 64
DIGEST_B = "sha256:" + "c" * 64


def gate_payload() -> dict:
    names = (
        ("Backend CI", ".github/workflows/backend-ci.yml", 101),
        ("Frontend CI", ".github/workflows/frontend-ci.yml", 102),
        ("Security Gate", ".github/workflows/security-gate.yml", 103),
        ("Deployment Validation", ".github/workflows/deployment-validation.yml", 104),
    )
    return {
        "repository": "owner/repo",
        "release_sha": SHA,
        "passed": True,
        "gates": [
            {
                "name": name,
                "path": path,
                "status": "completed",
                "conclusion": "success",
                "run_id": run_id,
                "html_url": f"https://github.com/owner/repo/actions/runs/{run_id}",
                "event": "push",
                "head_branch": "main",
                "head_sha": SHA,
            }
            for name, path, run_id in names
        ],
    }


def write_gates(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "gates.json"
    path.write_text(json.dumps(payload or gate_payload()), encoding="utf-8")
    return path


def build(tmp_path: Path, **overrides) -> dict:
    values = {
        "repository": "owner/repo",
        "dispatch_ref": "refs/heads/main",
        "workflow_sha": SHA,
        "protected_main_sha": SHA,
        "candidate_sha": SHA,
        "backend_digest": DIGEST_A,
        "frontend_digest": DIGEST_B,
        "gate_evidence_path": write_gates(tmp_path),
    }
    values.update(overrides)
    return build_manifest(**values)


def test_manifest_binds_repository_provenance_and_scope(tmp_path: Path):
    manifest = build(tmp_path)
    assert manifest["schema_version"] == 1
    assert manifest["provenance"]["workflow_sha"] == SHA
    assert manifest["candidate"]["candidate_sha"] == SHA
    assert [gate["name"] for gate in manifest["gates"]] == [
        "Backend CI",
        "Frontend CI",
        "Security Gate",
        "Deployment Validation",
    ]
    assert manifest["authorization_scope"] == {
        "external_staging_proven": False,
        "public_access_authorized": False,
        "repository_only": True,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dispatch_ref", "refs/heads/dev"),
        ("workflow_sha", "d" * 40),
        ("candidate_sha", "e" * 40),
        ("backend_digest", "latest"),
    ],
)
def test_manifest_rejects_invalid_provenance(tmp_path: Path, field: str, value: str):
    with pytest.raises(ValueError):
        build(tmp_path, **{field: value})


def test_manifest_rejects_failed_or_mismatched_gate_evidence(tmp_path: Path):
    payload = gate_payload()
    payload["gates"][0]["conclusion"] = "failure"
    with pytest.raises(ValueError, match="did not pass"):
        build(tmp_path, gate_evidence_path=write_gates(tmp_path, payload))

    payload = gate_payload()
    payload["release_sha"] = "f" * 40
    with pytest.raises(ValueError, match="SHA mismatch"):
        build(tmp_path, gate_evidence_path=write_gates(tmp_path, payload))


def test_atomic_output_is_deterministic(tmp_path: Path):
    manifest = build(tmp_path)
    output = tmp_path / "manifest.json"
    write_atomic(output, manifest)
    first = output.read_bytes()
    write_atomic(output, manifest)
    assert output.read_bytes() == first
    assert json.loads(first)["authorization_scope"]["external_staging_proven"] is False
