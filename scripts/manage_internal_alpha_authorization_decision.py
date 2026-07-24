#!/usr/bin/env python3
"""Write or verify a deterministic fail-closed Internal Alpha authorization decision."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
OUTCOMES = {"success", "failure", "cancelled", "skipped", "not-run"}
STEPS = (
    "release-gates",
    "manifest",
    "manifest-validation",
    "validate",
    "evidence",
    "checksum-inventory",
    "checksum-verification",
    "receipt",
    "receipt-verification",
)
SCOPE = {
    "external_staging_proven": False,
    "public_access_authorized": False,
    "repository_only": True,
}


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _validate_text(value: object, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    return value


def _normalize_steps(raw_steps: list[str]) -> list[dict[str, str]]:
    if len(raw_steps) != len(STEPS):
        raise ValueError("all canonical step outcomes are required")
    normalized: list[dict[str, str]] = []
    for expected, raw in zip(STEPS, raw_steps, strict=True):
        name, separator, outcome = raw.partition("=")
        if separator != "=" or name != expected:
            raise ValueError("step outcomes must use canonical names and ordering")
        if outcome not in OUTCOMES:
            raise ValueError(f"step {name} has an invalid outcome")
        normalized.append({"name": name, "outcome": outcome})
    return normalized


def build_decision(
    *,
    repository: str,
    run_id: int,
    run_attempt: int,
    workflow_sha: str,
    candidate_sha: str,
    backend_digest: str,
    frontend_digest: str,
    raw_steps: list[str],
) -> dict[str, object]:
    repository = _validate_text(repository, REPOSITORY_RE, "repository")
    workflow_sha = _validate_text(workflow_sha, SHA_RE, "workflow SHA")
    candidate_sha = _validate_text(candidate_sha, SHA_RE, "candidate SHA")
    backend_digest = _validate_text(backend_digest, DIGEST_RE, "backend digest")
    frontend_digest = _validate_text(frontend_digest, DIGEST_RE, "frontend digest")
    run_id = _positive_int(run_id, "run ID")
    run_attempt = _positive_int(run_attempt, "run attempt")
    steps = _normalize_steps(raw_steps)
    failed_steps = [step["name"] for step in steps if step["outcome"] != "success"]
    return {
        "authorization_scope": SCOPE,
        "authorized": not failed_steps,
        "candidate": {
            "backend_digest": backend_digest,
            "candidate_sha": candidate_sha,
            "frontend_digest": frontend_digest,
            "repository": repository,
        },
        "failed_steps": failed_steps,
        "provenance": {
            "run_attempt": run_attempt,
            "run_id": run_id,
            "workflow_sha": workflow_sha,
        },
        "schema_version": 1,
        "steps": steps,
    }


def write_decision(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_decision(path: Path, expected: dict[str, object]) -> None:
    if path.is_symlink() or not path.exists() or not path.is_file():
        raise ValueError("decision record is missing, symlinked, or not regular")
    try:
        actual = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read decision record: {exc}") from exc
    if actual != expected:
        raise ValueError("authorization decision does not match workflow outcomes")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--frontend-digest", required=True)
    parser.add_argument("--step", action="append", default=[], dest="steps")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = build_decision(
            repository=args.repository,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            workflow_sha=args.workflow_sha,
            candidate_sha=args.candidate_sha,
            backend_digest=args.backend_digest,
            frontend_digest=args.frontend_digest,
            raw_steps=args.steps,
        )
        if args.mode == "write":
            write_decision(args.output, payload)
        else:
            verify_decision(args.output, payload)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"{args.mode.upper()}: authorized={str(payload['authorized']).lower()} {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
