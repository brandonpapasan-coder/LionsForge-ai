#!/usr/bin/env python3
"""Validate a repository-only Internal Alpha authorization manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
RUN_URL_RE = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[1-9][0-9]*$"
)
REQUIRED_GATE_PATHS = {
    "Backend CI": ".github/workflows/backend-ci.yml",
    "Frontend CI": ".github/workflows/frontend-ci.yml",
    "Security Gate": ".github/workflows/security-gate.yml",
    "Deployment Validation": ".github/workflows/deployment-validation.yml",
}


def _exact_keys(value: object, expected: set[str], field: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    if set(value) != expected:
        raise ValueError(f"{field} keys are invalid")
    return value


def _match(pattern: re.Pattern[str], value: object, field: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value


def validate_manifest(payload: object) -> None:
    root = _exact_keys(
        payload,
        {"authorization_scope", "candidate", "gates", "provenance", "schema_version"},
        "manifest",
    )
    if root["schema_version"] != 1 or isinstance(root["schema_version"], bool):
        raise ValueError("schema_version must be 1")

    scope = _exact_keys(
        root["authorization_scope"],
        {"external_staging_proven", "public_access_authorized", "repository_only"},
        "authorization_scope",
    )
    if scope != {
        "external_staging_proven": False,
        "public_access_authorized": False,
        "repository_only": True,
    }:
        raise ValueError("authorization_scope weakens repository-only boundaries")

    provenance = _exact_keys(
        root["provenance"],
        {"dispatch_ref", "protected_main_sha", "repository", "workflow_sha"},
        "provenance",
    )
    repository = _match(REPOSITORY_RE, provenance["repository"], "repository")
    if provenance["dispatch_ref"] != "refs/heads/main":
        raise ValueError("dispatch_ref must be refs/heads/main")
    protected_main_sha = _match(SHA_RE, provenance["protected_main_sha"], "protected_main_sha")
    workflow_sha = _match(SHA_RE, provenance["workflow_sha"], "workflow_sha")

    candidate = _exact_keys(
        root["candidate"],
        {"backend_digest", "candidate_sha", "frontend_digest"},
        "candidate",
    )
    candidate_sha = _match(SHA_RE, candidate["candidate_sha"], "candidate_sha")
    _match(DIGEST_RE, candidate["backend_digest"], "backend_digest")
    _match(DIGEST_RE, candidate["frontend_digest"], "frontend_digest")
    if not (protected_main_sha == workflow_sha == candidate_sha):
        raise ValueError("protected-main, workflow, and candidate SHAs must match")

    gates = root["gates"]
    if not isinstance(gates, list) or len(gates) != len(REQUIRED_GATE_PATHS):
        raise ValueError("gates must contain exactly four entries")
    names: list[str] = []
    for index, raw_gate in enumerate(gates):
        gate = _exact_keys(
            raw_gate,
            {
                "conclusion",
                "event",
                "head_branch",
                "head_sha",
                "html_url",
                "name",
                "path",
                "run_id",
                "status",
            },
            f"gates[{index}]",
        )
        name = gate["name"]
        if not isinstance(name, str) or name not in REQUIRED_GATE_PATHS:
            raise ValueError(f"gates[{index}].name is invalid")
        names.append(name)
        if gate["path"] != REQUIRED_GATE_PATHS[name]:
            raise ValueError(f"gates[{index}].path is invalid")
        if gate["status"] != "completed" or gate["conclusion"] != "success":
            raise ValueError(f"gate did not pass: {name}")
        if gate["event"] != "push" or gate["head_branch"] != "main":
            raise ValueError(f"gate provenance is invalid: {name}")
        if gate["head_sha"] != candidate_sha:
            raise ValueError(f"gate SHA mismatch: {name}")
        run_id = gate["run_id"]
        if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
            raise ValueError(f"gate run_id is invalid: {name}")
        url = _match(RUN_URL_RE, gate["html_url"], f"gates[{index}].html_url")
        expected_prefix = f"https://github.com/{repository}/actions/runs/"
        if not url.startswith(expected_prefix) or not url.endswith(f"/{run_id}"):
            raise ValueError(f"gate URL does not match repository or run_id: {name}")

    if tuple(names) != tuple(REQUIRED_GATE_PATHS):
        raise ValueError("gates are duplicated, missing, or not in canonical order")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate_manifest(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"VALID: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
