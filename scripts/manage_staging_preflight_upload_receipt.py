#!/usr/bin/env python3
"""Write or verify a deterministic staging preflight artifact upload receipt."""

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


def validate_output_path(*, output: Path, report: Path) -> None:
    if output.is_symlink():
        raise ValueError("upload receipt output must not be a symlink")
    if output.resolve(strict=False) == report.resolve(strict=False):
        raise ValueError("upload receipt output must be distinct from preflight report")


def build_receipt(
    *,
    report: Path,
    artifact_name: str,
    artifact_id: int,
    artifact_url: str,
    artifact_digest: str,
) -> dict[str, object]:
    report_value = _read_object(report, "preflight report")
    if report_value.get("schema_version") != 1 or report_value.get("status") != "passed":
        raise ValueError("preflight report must be schema version 1 with passed status")

    provenance = report_value.get("provenance")
    required = {
        "candidate_sha",
        "generated_at",
        "repository",
        "skip_endpoints",
        "workflow_run_attempt",
        "workflow_run_id",
        "workflow_run_url",
    }
    if not isinstance(provenance, dict) or set(provenance) != required:
        raise ValueError("preflight report provenance is invalid")

    candidate_sha = _text(provenance["candidate_sha"], SHA_RE, "candidate SHA")
    repository = _text(provenance["repository"], REPOSITORY_RE, "repository")
    run_id = _positive_int(provenance["workflow_run_id"], "workflow run ID")
    run_attempt = _positive_int(provenance["workflow_run_attempt"], "workflow run attempt")
    if not isinstance(provenance["skip_endpoints"], bool):
        raise ValueError("skip_endpoints must be boolean")
    expected_run_url = f"https://github.com/{repository}/actions/runs/{run_id}"
    if provenance["workflow_run_url"] != expected_run_url:
        raise ValueError("workflow run URL does not match repository and run ID")

    artifact_name = _text(artifact_name, ARTIFACT_RE, "artifact name")
    if artifact_name != f"staging-preflight-{candidate_sha}":
        raise ValueError("artifact name does not match candidate SHA")
    artifact_id = _positive_int(artifact_id, "artifact ID")
    artifact_digest = _text(artifact_digest, DIGEST_RE, "artifact digest")
    expected_url = f"{expected_run_url}/artifacts/{artifact_id}"
    if artifact_url != expected_url:
        raise ValueError("artifact URL does not match repository, run ID, and artifact ID")

    return {
        "artifact": {
            "digest": artifact_digest,
            "id": artifact_id,
            "name": artifact_name,
            "url": artifact_url,
        },
        "candidate": {"candidate_sha": candidate_sha, "repository": repository},
        "preflight": {
            "path": report.as_posix(),
            "sha256": _sha256(report),
            "size_bytes": report.stat().st_size,
            "skip_endpoints": provenance["skip_endpoints"],
        },
        "provenance": {
            "run_attempt": run_attempt,
            "run_id": run_id,
            "run_url": expected_run_url,
        },
        "schema_version": 1,
    }


def write_receipt(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_receipt(path: Path, expected: dict[str, object]) -> None:
    if _read_object(path, "upload receipt") != expected:
        raise ValueError("staging preflight upload receipt does not match verified sources")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "verify"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--artifact-url", required=True)
    parser.add_argument("--artifact-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_output_path(output=args.output, report=args.report)
        payload = build_receipt(
            report=args.report,
            artifact_name=args.artifact_name,
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
    print(f"{args.mode.upper()}: artifact_id={args.artifact_id} {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
