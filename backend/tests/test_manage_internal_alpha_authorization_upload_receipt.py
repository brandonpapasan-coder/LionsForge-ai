from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "manage_internal_alpha_authorization_upload_receipt.py"
SCOPE = {
    "external_staging_proven": False,
    "public_access_authorized": False,
    "repository_only": True,
}
REPOSITORY = "brandonpapasan-coder/LionsForge-ai"
RUN_ID = 123456789
ARTIFACT_ID = 987654321
ARTIFACT_URL = (
    f"https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}/artifacts/{ARTIFACT_ID}"
)
ARTIFACT_DIGEST = "sha256:" + "a" * 64


def publication() -> dict[str, object]:
    return {
        "artifact": {
            "contract_path": "internal-alpha-authorization-artifact-contract.json",
            "contract_sha256": "b" * 64,
            "contract_size_bytes": 321,
            "name": "internal-alpha-authorization-evidence",
        },
        "authorization_scope": SCOPE,
        "authorized": True,
        "candidate": {
            "backend_digest": "sha256:" + "c" * 64,
            "candidate_sha": "d" * 40,
            "frontend_digest": "sha256:" + "e" * 64,
            "repository": REPOSITORY,
        },
        "provenance": {
            "run_attempt": 2,
            "run_id": RUN_ID,
            "workflow_sha": "f" * 40,
        },
        "schema_version": 1,
    }


def run_tool(
    mode: str,
    source: Path,
    output: Path,
    **overrides: object,
) -> subprocess.CompletedProcess[str]:
    values = {
        "artifact_id": ARTIFACT_ID,
        "artifact_url": ARTIFACT_URL,
        "artifact_digest": ARTIFACT_DIGEST,
    }
    values.update(overrides)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            mode,
            "--publication",
            str(source),
            "--artifact-id",
            str(values["artifact_id"]),
            "--artifact-url",
            str(values["artifact_url"]),
            "--artifact-digest",
            str(values["artifact_digest"]),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def write_publication(path: Path, value: dict[str, object] | None = None) -> None:
    path.write_text(json.dumps(value or publication(), indent=2, sort_keys=True) + "\n")


def test_write_and_verify_upload_receipt(tmp_path: Path):
    source = tmp_path / "publication.json"
    output = tmp_path / "receipt.json"
    write_publication(source)

    assert run_tool("write", source, output).returncode == 0
    assert run_tool("verify", source, output).returncode == 0

    value = json.loads(output.read_text())
    assert value["artifact"] == {
        "digest": ARTIFACT_DIGEST,
        "id": ARTIFACT_ID,
        "name": "internal-alpha-authorization-evidence",
        "url": ARTIFACT_URL,
    }
    assert value["authorization_scope"] == SCOPE
    assert value["publication"]["path"] == str(source)


def test_output_is_deterministic(tmp_path: Path):
    source = tmp_path / "publication.json"
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_publication(source)

    assert run_tool("write", source, first).returncode == 0
    assert run_tool("write", source, second).returncode == 0
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("authorization_scope", {"repository_only": True}),
        ("schema_version", 2),
        ("authorized", "true"),
    ],
)
def test_rejects_invalid_publication(tmp_path: Path, field: str, value: object):
    source = tmp_path / "publication.json"
    output = tmp_path / "receipt.json"
    payload = publication()
    payload[field] = value
    write_publication(source, payload)

    result = run_tool("write", source, output)
    assert result.returncode == 1
    assert not output.exists()


def test_rejects_inconsistent_artifact_url(tmp_path: Path):
    source = tmp_path / "publication.json"
    output = tmp_path / "receipt.json"
    write_publication(source)

    result = run_tool(
        "write",
        source,
        output,
        artifact_url="https://github.com/other/repo/actions/runs/1/artifacts/2",
    )
    assert result.returncode == 1
    assert "artifact URL does not match" in result.stderr


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("artifact_id", 0),
        ("artifact_digest", "sha256:bad"),
    ],
)
def test_rejects_invalid_upload_identity(tmp_path: Path, key: str, value: object):
    source = tmp_path / "publication.json"
    output = tmp_path / "receipt.json"
    write_publication(source)

    result = run_tool("write", source, output, **{key: value})
    assert result.returncode == 1
    assert not output.exists()


def test_rejects_symlinked_publication(tmp_path: Path):
    target = tmp_path / "target.json"
    source = tmp_path / "publication.json"
    output = tmp_path / "receipt.json"
    write_publication(target)
    source.symlink_to(target)

    assert run_tool("write", source, output).returncode == 1


def test_rejects_output_aliasing_publication(tmp_path: Path):
    source = tmp_path / "publication.json"
    write_publication(source)

    assert run_tool("write", source, source).returncode == 1


def test_verify_rejects_tampering_and_source_mutation(tmp_path: Path):
    source = tmp_path / "publication.json"
    output = tmp_path / "receipt.json"
    write_publication(source)
    assert run_tool("write", source, output).returncode == 0

    value = json.loads(output.read_text())
    value["artifact"]["id"] += 1
    output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    assert run_tool("verify", source, output).returncode == 1

    assert run_tool("write", source, output).returncode == 0
    payload = publication()
    payload["authorized"] = False
    write_publication(source, payload)
    assert run_tool("verify", source, output).returncode == 1
