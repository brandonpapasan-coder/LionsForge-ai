#!/usr/bin/env python3
"""Write a deterministic repository-only Internal Alpha authorization manifest."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REQUIRED_GATE_NAMES = (
    "Backend CI",
    "Frontend CI",
    "Security Gate",
    "Deployment Validation",
)


def _require(pattern: re.Pattern[str], value: str, field: str) -> str:
    if not pattern.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value


def _load_gate_evidence(path: Path, repository: str, candidate_sha: str) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"release gate evidence is unreadable: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("release gate evidence must be an object")
    if payload.get("repository") != repository:
        raise ValueError("release gate evidence repository mismatch")
    if payload.get("release_sha") != candidate_sha:
        raise ValueError("release gate evidence SHA mismatch")
    if payload.get("passed") is not True:
        raise ValueError("release gate evidence must report passed=true")
    gates = payload.get("gates")
    if not isinstance(gates, list) or len(gates) != len(REQUIRED_GATE_NAMES):
        raise ValueError("release gate evidence must contain exactly four gates")

    normalized: list[dict] = []
    seen: set[str] = set()
    for gate in gates:
        if not isinstance(gate, dict):
            raise ValueError("release gate entry must be an object")
        name = gate.get("name")
        if name not in REQUIRED_GATE_NAMES or name in seen:
            raise ValueError("release gate names are invalid or duplicated")
        seen.add(name)
        if gate.get("status") != "completed" or gate.get("conclusion") != "success":
            raise ValueError(f"release gate did not pass: {name}")
        if gate.get("event") != "push" or gate.get("head_branch") != "main":
            raise ValueError(f"release gate provenance is invalid: {name}")
        if gate.get("head_sha") != candidate_sha:
            raise ValueError(f"release gate SHA mismatch: {name}")
        run_id = gate.get("run_id")
        if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
            raise ValueError(f"release gate run_id is invalid: {name}")
        path_value = gate.get("path")
        url = gate.get("html_url")
        if not isinstance(path_value, str) or not path_value.startswith(".github/workflows/"):
            raise ValueError(f"release gate path is invalid: {name}")
        if not isinstance(url, str) or not url.startswith("https://github.com/"):
            raise ValueError(f"release gate URL is invalid: {name}")
        normalized.append(
            {
                "conclusion": "success",
                "event": "push",
                "head_branch": "main",
                "head_sha": candidate_sha,
                "html_url": url,
                "name": name,
                "path": path_value,
                "run_id": run_id,
                "status": "completed",
            }
        )

    if tuple(gate["name"] for gate in normalized) != REQUIRED_GATE_NAMES:
        raise ValueError("release gates are not in canonical order")
    return normalized


def build_manifest(
    *,
    repository: str,
    dispatch_ref: str,
    workflow_sha: str,
    protected_main_sha: str,
    candidate_sha: str,
    backend_digest: str,
    frontend_digest: str,
    gate_evidence_path: Path,
) -> dict:
    _require(REPOSITORY_RE, repository, "repository")
    if dispatch_ref != "refs/heads/main":
        raise ValueError("dispatch_ref must be refs/heads/main")
    for field, value in (
        ("workflow_sha", workflow_sha),
        ("protected_main_sha", protected_main_sha),
        ("candidate_sha", candidate_sha),
    ):
        _require(SHA_RE, value, field)
    if workflow_sha != protected_main_sha:
        raise ValueError("workflow_sha must equal protected_main_sha")
    if candidate_sha != protected_main_sha:
        raise ValueError("candidate_sha must equal protected_main_sha")
    _require(DIGEST_RE, backend_digest, "backend_digest")
    _require(DIGEST_RE, frontend_digest, "frontend_digest")
    gates = _load_gate_evidence(gate_evidence_path, repository, candidate_sha)
    return {
        "authorization_scope": {
            "external_staging_proven": False,
            "public_access_authorized": False,
            "repository_only": True,
        },
        "candidate": {
            "backend_digest": backend_digest,
            "candidate_sha": candidate_sha,
            "frontend_digest": frontend_digest,
        },
        "gates": gates,
        "provenance": {
            "dispatch_ref": dispatch_ref,
            "protected_main_sha": protected_main_sha,
            "repository": repository,
            "workflow_sha": workflow_sha,
        },
        "schema_version": 1,
    }


def write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(rendered)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--dispatch-ref", required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--protected-main-sha", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--frontend-digest", required=True)
    parser.add_argument("--gate-evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_manifest(
            repository=args.repository,
            dispatch_ref=args.dispatch_ref,
            workflow_sha=args.workflow_sha,
            protected_main_sha=args.protected_main_sha,
            candidate_sha=args.candidate_sha,
            backend_digest=args.backend_digest,
            frontend_digest=args.frontend_digest,
            gate_evidence_path=args.gate_evidence,
        )
        write_atomic(args.output, manifest)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
