#!/usr/bin/env python3
"""Verify retained launch evidence-chain artifacts against GitHub run metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_FILES = 8
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024
EXPECTED_PRIMARY_FILES = {
    "launch-evidence-chain-receipt.json",
    "launch-evidence-chain-validation.txt",
}
EXPECTED_PROVENANCE_FILES = {"launch-evidence-chain-upload-receipt.json"}


def _read_json(path: Path, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} is missing, symlinked, or not regular")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_extract(zip_path: Path, destination: Path, expected_files: set[str]) -> None:
    if zip_path.is_symlink() or not zip_path.is_file():
        raise ValueError("artifact archive is missing, symlinked, or not regular")
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_FILES:
            raise ValueError("artifact archive file count is invalid")
        names: set[str] = set()
        total = 0
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
                raise ValueError("artifact archive contains an unsafe path")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or info.is_dir():
                raise ValueError("artifact archive contains a symlink or directory")
            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("artifact archive exceeds the replay size limit")
            names.add(path.name)
        if names != expected_files:
            raise ValueError("artifact archive contents do not match the expected contract")
        for info in infos:
            target = destination / PurePosixPath(info.filename).name
            with archive.open(info) as source, target.open("xb") as output:
                output.write(source.read())


def verify_replay(
    *,
    primary_dir: Path,
    provenance_dir: Path,
    candidate_sha: str,
    repository: str,
    workflow_name: str,
    workflow_sha: str,
    run_id: int,
    run_attempt: int,
    artifact_id: int,
    artifact_name: str,
    artifact_url: str,
    artifact_digest: str,
) -> dict[str, object]:
    if not SHA_RE.fullmatch(candidate_sha) or not SHA_RE.fullmatch(workflow_sha):
        raise ValueError("candidate or workflow SHA is invalid")
    if not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("repository is invalid")
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in (run_id, run_attempt, artifact_id)):
        raise ValueError("run and artifact identifiers must be positive integers")
    if not DIGEST_RE.fullmatch(artifact_digest):
        raise ValueError("artifact digest is invalid")
    expected_name = f"launch-evidence-chain-{candidate_sha}"
    if artifact_name != expected_name:
        raise ValueError("primary artifact name does not match candidate")
    expected_url = f"https://github.com/{repository}/actions/runs/{run_id}/artifacts/{artifact_id}"
    if artifact_url != expected_url:
        raise ValueError("artifact URL does not match repository, run ID, and artifact ID")

    source_path = primary_dir / "launch-evidence-chain-receipt.json"
    upload_path = provenance_dir / "launch-evidence-chain-upload-receipt.json"
    source = _read_json(source_path, "source chain receipt")
    upload = _read_json(upload_path, "upload receipt")
    if source.get("schema") != "lionsforge.launch-evidence-chain-receipt" or source.get("result") != "VALID":
        raise ValueError("source chain receipt is not a supported VALID receipt")
    if upload.get("schema") != "lionsforge.launch-evidence-chain-upload-receipt" or upload.get("schema_version") != 1:
        raise ValueError("upload receipt schema is invalid")

    expected_scope = {
        "deployment_authorized": False,
        "general_availability_authorized": False,
        "payment_collection_authorized": False,
        "public_access_authorized": False,
        "repository_only": True,
    }
    if upload.get("authorization_scope") != expected_scope:
        raise ValueError("upload receipt weakens repository-only authorization boundaries")
    expected_artifact = {"digest": artifact_digest, "id": artifact_id, "name": artifact_name, "url": artifact_url}
    expected_candidate = {"candidate_sha": candidate_sha, "repository": repository}
    expected_provenance = {
        "run_attempt": run_attempt,
        "run_id": run_id,
        "workflow_name": workflow_name,
        "workflow_sha": workflow_sha,
    }
    if upload.get("artifact") != expected_artifact:
        raise ValueError("upload receipt artifact binding does not match replay metadata")
    if upload.get("candidate") != expected_candidate:
        raise ValueError("upload receipt candidate binding does not match replay metadata")
    if upload.get("provenance") != expected_provenance:
        raise ValueError("upload receipt provenance does not match replay metadata")
    expected_source = {
        "path": "launch-evidence-chain-receipt.json",
        "sha256": _sha256(source_path),
        "size_bytes": source_path.stat().st_size,
    }
    if upload.get("source_receipt") != expected_source:
        raise ValueError("upload receipt source binding does not match extracted receipt")

    return {
        "schema": "lionsforge.launch-evidence-chain-artifact-replay",
        "schema_version": 1,
        "result": "VALID",
        "candidate_sha": candidate_sha,
        "repository": repository,
        "workflow_name": workflow_name,
        "workflow_sha": workflow_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "artifact_id": artifact_id,
        "artifact_name": artifact_name,
        "artifact_digest": artifact_digest,
        "source_receipt_sha256": expected_source["sha256"],
        "authorization_scope": expected_scope,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-zip", type=Path, required=True)
    parser.add_argument("--provenance-zip", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--artifact-url", required=True)
    parser.add_argument("--artifact-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        primary_dir = args.workdir / "primary"
        provenance_dir = args.workdir / "provenance"
        safe_extract(args.primary_zip, primary_dir, EXPECTED_PRIMARY_FILES)
        safe_extract(args.provenance_zip, provenance_dir, EXPECTED_PROVENANCE_FILES)
        result = verify_replay(
            primary_dir=primary_dir,
            provenance_dir=provenance_dir,
            candidate_sha=args.candidate_sha,
            repository=args.repository,
            workflow_name=args.workflow_name,
            workflow_sha=args.workflow_sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            artifact_id=args.artifact_id,
            artifact_name=args.artifact_name,
            artifact_url=args.artifact_url,
            artifact_digest=args.artifact_digest,
        )
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"VALID: run_id={args.run_id} candidate={args.candidate_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
