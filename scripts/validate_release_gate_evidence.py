#!/usr/bin/env python3
"""Validate persisted release-gate evidence independently of the API verifier."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_WORKFLOW_PATHS = {
    "Backend CI": ".github/workflows/backend-ci.yml",
    "Frontend CI": ".github/workflows/frontend-ci.yml",
    "Security Gate": ".github/workflows/security-gate.yml",
    "Deployment Validation": ".github/workflows/deployment-validation.yml",
}
REQUIRED_EVENT = "push"
REQUIRED_BRANCH = "main"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TOP_LEVEL_KEYS = {
    "repository",
    "release_sha",
    "required_event",
    "required_branch",
    "required_workflow_paths",
    "passed",
    "gates",
}
GATE_KEYS = {
    "name",
    "path",
    "status",
    "conclusion",
    "run_id",
    "html_url",
    "event",
    "head_branch",
    "head_sha",
}


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field)


def validate_payload(payload: object, repository: str, release_sha: str) -> None:
    if not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("repository must use owner/name format")
    if not SHA_RE.fullmatch(release_sha):
        raise ValueError("release SHA must be 40 lowercase hexadecimal characters")
    if not isinstance(payload, dict):
        raise ValueError("evidence must be a JSON object")
    if set(payload) != TOP_LEVEL_KEYS:
        raise ValueError("evidence has missing or unexpected top-level fields")
    if payload["repository"] != repository:
        raise ValueError("evidence repository does not match the requested repository")
    if payload["release_sha"] != release_sha:
        raise ValueError("evidence release_sha does not match the requested SHA")
    if payload["required_event"] != REQUIRED_EVENT:
        raise ValueError("evidence required_event is invalid")
    if payload["required_branch"] != REQUIRED_BRANCH:
        raise ValueError("evidence required_branch is invalid")
    if payload["required_workflow_paths"] != REQUIRED_WORKFLOW_PATHS:
        raise ValueError("evidence required workflow map is invalid")
    if not isinstance(payload["passed"], bool):
        raise ValueError("evidence passed must be a boolean")

    gates = payload["gates"]
    if not isinstance(gates, list) or len(gates) != len(REQUIRED_WORKFLOW_PATHS):
        raise ValueError("evidence must contain exactly one gate per required workflow")

    recomputed_passed = True
    for index, (workflow_name, workflow_path) in enumerate(
        REQUIRED_WORKFLOW_PATHS.items()
    ):
        gate = gates[index]
        if not isinstance(gate, dict) or set(gate) != GATE_KEYS:
            raise ValueError(f"gate {index} has missing or unexpected fields")
        if gate["name"] != workflow_name or gate["path"] != workflow_path:
            raise ValueError(f"gate {index} identity or path is invalid")

        status = _required_string(gate["status"], f"gate {index} status")
        conclusion = _optional_string(gate["conclusion"], f"gate {index} conclusion")
        event = _optional_string(gate["event"], f"gate {index} event")
        branch = _optional_string(gate["head_branch"], f"gate {index} head_branch")
        head_sha = _optional_string(gate["head_sha"], f"gate {index} head_sha")
        html_url = _optional_string(gate["html_url"], f"gate {index} html_url")
        run_id = gate["run_id"]

        if head_sha is not None and not SHA_RE.fullmatch(head_sha):
            raise ValueError(f"gate {index} head_sha is invalid")
        if run_id is not None and (
            not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0
        ):
            raise ValueError(f"gate {index} run_id is invalid")
        if html_url is not None and not html_url.startswith("https://github.com/"):
            raise ValueError(f"gate {index} html_url is invalid")

        gate_passed = (
            status == "completed"
            and conclusion == "success"
            and event == REQUIRED_EVENT
            and branch == REQUIRED_BRANCH
            and head_sha == release_sha
            and run_id is not None
        )
        recomputed_passed = recomputed_passed and gate_passed

    if payload["passed"] != recomputed_passed:
        raise ValueError("evidence passed value is inconsistent with gate results")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--sha", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.evidence.read_text(encoding="utf-8"))
        validate_payload(payload, args.repository, args.sha)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("VALID: release gate evidence artifact is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
