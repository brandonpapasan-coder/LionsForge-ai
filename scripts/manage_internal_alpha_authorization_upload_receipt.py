#!/usr/bin/env python3
"""Write or verify a deterministic Internal Alpha authorization upload receipt."""

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
SCOPE = {
    "external_staging_proven": False,
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


def validate_output_path(*, output: Path, publication: Path) -> None:
    if output.is_symlink():
        raise ValueError("upload receipt output must not be a symlink")
    if output.resolve(strict=False) == publication.resolve(strict=False):
        raise ValueError("upload receipt output must be distinct from publication record")


def build_receipt(
    *,
    publication: Path,
    artifact_id: int,
    artifact_url: str,
    artifact_digest: str,
) -> dict[str, object]:
    publication_value = _read_object(publication, "publication record")
    publication_keys = {
        "artifact",
        "authorization_scope",
        "authorized",
        "candidate",
        "provenance",
        "schema_version",
    }
    if set(publication_value) != publication_keys:
        raise ValueError("publication record keys are invalid")
    if publication_value["schema_version"] != 1:
        raise ValueError("publication schema_version must be 1")
    if publication_value["authorization_scope"] != SCOPE:
        raise ValueError("publication record weakens repository-only boundaries")
    authorized = publication_value["authorized"]
    if not isinstance(authorized, bool):
        raise ValueError("publication authorization state is invalid")

    artifact = publication_value["artifact"]
    candidate = publication_value["candidate"]
    provenance = publication_value["provenance"]
    if not isinstance(artifact, dict) or set(artifact) != {
        "contract_path",
        "contract_sha256",
        "contract_size_bytes",
        "name",
    }:
        raise ValueError("publication artifact is invalid")
    if not isinstance(candidate, dict) or set(candidate) != {
        "backend_digest",
        "candidate_sha",
        "frontend_digest",
        "repository",
    }:
        raise ValueError("publication candidate is invalid")
    if not isinstance(provenance, dict) or set(provenance) != {
        "run_attempt",
        "run_id",
        "workflow_sha",
    }:
        raise ValueError("publication provenance is invalid")

    name = _text(artifact["name"], ARTIFACT_RE, "artifact name")
    repository = _text(candidate["repository"], REPOSITORY_RE, "repository")
    candidate_sha = _text(candidate["candidate_sha"], SHA_RE, "candidate SHA")
    backend_digest = _text(candidate["backend_digest"], DIGEST_RE, "backend digest")
    frontend_digest = _text(candidate["frontend_digest"], DIGEST_RE, "frontend digest")
    workflow_sha = _text(provenance["workflow_sha"], SHA_RE, "workflow SHA")
    run_id = _positive_int(provenance["run_id"], "run ID")
    run_attempt = _positive_int(provenance["run_attempt"], "run attempt")
    artifact_id = _positive_int(artifact_id, "artifact ID")
    artifact_digest = _text(artifact_digest, DIGEST_RE, "artifact digest")

    expected_url = f"https://github.com/{repository}/actions/runs/{run_id}/artifacts/{artifact_id}"
    if artifact_url != expected_url:
        raise ValueError("artifact URL does not match repository, run ID, and artifact ID")

    return {
        "artifact": {
            "digest": artifact_digest,
            "id": artifact_id,
            "name": name,
            "url": artifact_url,
        },
        "authorization_scope": SCOPE,
        "authorized": authorized,
        "candidate": {
            "backend_digest": backend_digest,
            "candidate_sha": candidate_sha,
            "frontend_digest": frontend_digest,
            "repository": repository,
        },
        "provenance": {
            "run_attempt": run_attempt,
            "run_id": run_id,
            "workflow_sha": workflow_sha,
        },
        "publication": {
            "path": publication.as_posix(),
            "sha256": _sha256(publication),
            "size_bytes": publication.stat().st_size,
        },
        "schema_version": 1,
    }


def write_receipt(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def verify_receipt(path: Path, expected: dict[str, object]) -> None:
    actual = _read_object(path, "upload receipt")
    if actual != expected:
        raise ValueError("authorization upload receipt does not match verified sources")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "verify"))
    parser.add_argument("--publication", type=Path, required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--artifact-url", required=True)
    parser.add_argument("--artifact-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_output_path(output=args.output, publication=args.publication)
        payload = build_receipt(
            publication=args.publication,
            artifact_id=args.artifact_id,
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
    print(
        f"{args.mode.upper()}: authorized={str(payload['authorized']).lower()} "
        f"artifact_id={args.artifact_id} {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
