#!/usr/bin/env python3
"""Write or verify a deterministic launch evidence-chain artifact upload receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ARTIFACT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
WORKFLOW_RE = re.compile(r"^[A-Za-z0-9_. -]+$")
SCOPE = {
    "deployment_authorized": False,
    "general_availability_authorized": False,
    "payment_collection_authorized": False,
    "public_access_authorized": False,
    "repository_only": True,
}


def _regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.exists() or not path.is_file():
        raise ValueError(f"{label} is missing, symlinked, or not regular")


def _read_object(path: Path, label: str) -> dict[str, object]:
    _regular_file(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _text(value: object, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    return value


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_output_path(*, output: Path, source_receipt: Path) -> None:
    if output.is_symlink():
        raise ValueError("upload receipt output must not be a symlink")
    if output.resolve(strict=False) == source_receipt.resolve(strict=False):
        raise ValueError("upload receipt output must be distinct from source receipt")


def build_receipt(
    *,
    source_receipt: Path,
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
    source_value = _read_object(source_receipt, "source chain receipt")
    if source_value.get("schema") != "lionsforge.launch-evidence-chain-receipt":
        raise ValueError("source receipt schema is invalid")
    if source_value.get("schema_version") != 1 or source_value.get("result") != "VALID":
        raise ValueError("source receipt is not a supported VALID receipt")

    candidate_sha = _text(candidate_sha, SHA_RE, "candidate SHA")
    repository = _text(repository, REPOSITORY_RE, "repository")
    workflow_name = _text(workflow_name, WORKFLOW_RE, "workflow name")
    workflow_sha = _text(workflow_sha, SHA_RE, "workflow SHA")
    artifact_name = _text(artifact_name, ARTIFACT_RE, "artifact name")
    artifact_digest = _text(artifact_digest, DIGEST_RE, "artifact digest")
    run_id = _positive_int(run_id, "run ID")
    run_attempt = _positive_int(run_attempt, "run attempt")
    artifact_id = _positive_int(artifact_id, "artifact ID")

    expected_url = f"https://github.com/{repository}/actions/runs/{run_id}/artifacts/{artifact_id}"
    if artifact_url != expected_url:
        raise ValueError("artifact URL does not match repository, run ID, and artifact ID")

    return {
        "artifact": {
            "digest": artifact_digest,
            "id": artifact_id,
            "name": artifact_name,
            "url": artifact_url,
        },
        "authorization_scope": SCOPE,
        "candidate": {
            "candidate_sha": candidate_sha,
            "repository": repository,
        },
        "provenance": {
            "run_attempt": run_attempt,
            "run_id": run_id,
            "workflow_name": workflow_name,
            "workflow_sha": workflow_sha,
        },
        "schema": "lionsforge.launch-evidence-chain-upload-receipt",
        "schema_version": 1,
        "source_receipt": {
            "path": source_receipt.as_posix(),
            "sha256": _sha256(source_receipt),
            "size_bytes": source_receipt.stat().st_size,
        },
    }


def write_receipt(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_receipt(path: Path, expected: dict[str, object]) -> None:
    if _read_object(path, "upload receipt") != expected:
        raise ValueError("launch evidence-chain upload receipt does not match verified sources")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "verify"))
    parser.add_argument("--source-receipt", type=Path, required=True)
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_output_path(output=args.output, source_receipt=args.source_receipt)
        payload = build_receipt(
            source_receipt=args.source_receipt,
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
        if args.mode == "write":
            write_receipt(args.output, payload)
        else:
            verify_receipt(args.output, payload)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"{args.mode.upper()}: artifact_id={args.artifact_id} {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
