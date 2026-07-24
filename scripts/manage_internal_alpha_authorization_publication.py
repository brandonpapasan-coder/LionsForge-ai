#!/usr/bin/env python3
"""Write or verify a deterministic Internal Alpha authorization publication record."""

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


def build_publication(
    *, decision: Path, contract: Path, artifact_name: str
) -> dict[str, object]:
    if decision == contract:
        raise ValueError("decision and artifact contract must be distinct files")
    decision_value = _read_object(decision, "decision record")
    contract_value = _read_object(contract, "artifact contract")

    decision_keys = {
        "authorization_scope",
        "authorized",
        "candidate",
        "failed_steps",
        "provenance",
        "schema_version",
        "steps",
    }
    contract_keys = {
        "authorization_scope",
        "authorized",
        "files",
        "required_paths",
        "schema_version",
    }
    if set(decision_value) != decision_keys:
        raise ValueError("decision record keys are invalid")
    if set(contract_value) != contract_keys:
        raise ValueError("artifact contract keys are invalid")
    if decision_value["schema_version"] != 1 or contract_value["schema_version"] != 1:
        raise ValueError("source schema_version must be 1")
    if decision_value["authorization_scope"] != SCOPE or contract_value["authorization_scope"] != SCOPE:
        raise ValueError("source records weaken repository-only boundaries")

    authorized = decision_value["authorized"]
    if not isinstance(authorized, bool) or contract_value["authorized"] is not authorized:
        raise ValueError("source authorization state is invalid or inconsistent")

    candidate = decision_value["candidate"]
    provenance = decision_value["provenance"]
    if not isinstance(candidate, dict) or set(candidate) != {
        "backend_digest",
        "candidate_sha",
        "frontend_digest",
        "repository",
    }:
        raise ValueError("decision candidate is invalid")
    if not isinstance(provenance, dict) or set(provenance) != {
        "run_attempt",
        "run_id",
        "workflow_sha",
    }:
        raise ValueError("decision provenance is invalid")

    artifact_name = _text(artifact_name, ARTIFACT_RE, "artifact name")
    repository = _text(candidate["repository"], REPOSITORY_RE, "repository")
    candidate_sha = _text(candidate["candidate_sha"], SHA_RE, "candidate SHA")
    backend_digest = _text(candidate["backend_digest"], DIGEST_RE, "backend digest")
    frontend_digest = _text(candidate["frontend_digest"], DIGEST_RE, "frontend digest")
    workflow_sha = _text(provenance["workflow_sha"], SHA_RE, "workflow SHA")
    run_id = _positive_int(provenance["run_id"], "run ID")
    run_attempt = _positive_int(provenance["run_attempt"], "run attempt")

    return {
        "artifact": {
            "contract_path": contract.as_posix(),
            "contract_sha256": _sha256(contract),
            "contract_size_bytes": contract.stat().st_size,
            "name": artifact_name,
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
        "schema_version": 1,
    }


def write_publication(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_publication(path: Path, expected: dict[str, object]) -> None:
    actual = _read_object(path, "publication record")
    if actual != expected:
        raise ValueError("authorization publication record does not match verified sources")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "verify"))
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = build_publication(
            decision=args.decision,
            contract=args.contract,
            artifact_name=args.artifact_name,
        )
        if args.mode == "write":
            write_publication(args.output, payload)
        else:
            verify_publication(args.output, payload)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        f"{args.mode.upper()}: authorized={str(payload['authorized']).lower()} "
        f"artifact={args.artifact_name} {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
