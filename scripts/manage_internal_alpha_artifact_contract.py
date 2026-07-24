#!/usr/bin/env python3
"""Write or verify a fail-closed Internal Alpha authorization artifact contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

DECISION_PATH = "internal-alpha-authorization-decision.json"
DIAGNOSTIC_REQUIRED = (
    DECISION_PATH,
    "internal-alpha-authorization-decision-generation.txt",
    "internal-alpha-authorization-decision-verification.txt",
)
AUTHORIZED_REQUIRED = (
    "internal-alpha-release-gate-evidence.json",
    "internal-alpha-release-gate-evidence.txt",
    "internal-alpha-authorization-manifest.json",
    "internal-alpha-authorization-manifest.txt",
    "internal-alpha-authorization-manifest-validation.txt",
    "internal-alpha-readiness-validation.txt",
    "internal-alpha-evidence-validation.txt",
    "internal-alpha-authorization-evidence-checksums.json",
    "internal-alpha-authorization-evidence-checksum-generation.txt",
    "internal-alpha-authorization-evidence-checksum-verification.txt",
    "internal-alpha-authorization-receipt.json",
    "internal-alpha-authorization-receipt-generation.txt",
    "internal-alpha-authorization-receipt-verification.txt",
    *DIAGNOSTIC_REQUIRED,
)
ALLOWED_PATHS = frozenset(AUTHORIZED_REQUIRED)
SCOPE = {
    "external_staging_proven": False,
    "public_access_authorized": False,
    "repository_only": True,
}


def _regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.exists() or not path.is_file():
        raise ValueError(f"{label} is missing, symlinked, or not regular")


def _read_decision(path: Path) -> bool:
    _regular_file(path, "decision record")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read decision record: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("decision record must be an object")
    expected_keys = {
        "authorization_scope",
        "authorized",
        "candidate",
        "failed_steps",
        "provenance",
        "schema_version",
        "steps",
    }
    if set(value) != expected_keys:
        raise ValueError("decision record keys are invalid")
    if value["schema_version"] != 1 or isinstance(value["schema_version"], bool):
        raise ValueError("decision record schema_version must be 1")
    if value["authorization_scope"] != SCOPE:
        raise ValueError("decision record weakens repository-only boundaries")
    authorized = value["authorized"]
    if not isinstance(authorized, bool):
        raise ValueError("decision record authorized must be boolean")
    failed_steps = value["failed_steps"]
    if not isinstance(failed_steps, list) or not all(isinstance(item, str) for item in failed_steps):
        raise ValueError("decision record failed_steps is invalid")
    if authorized == bool(failed_steps):
        raise ValueError("decision record authorization conflicts with failed_steps")
    return authorized


def _binding(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"path": path.as_posix(), "sha256": digest.hexdigest(), "size_bytes": size}


def build_contract(*, decision: Path, contract: Path, files: list[Path]) -> dict[str, object]:
    if decision.as_posix() != DECISION_PATH:
        raise ValueError(f"decision record path must be {DECISION_PATH}")
    if not files:
        raise ValueError("at least one artifact path is required")
    paths = [path.as_posix() for path in files]
    if len(paths) != len(set(paths)):
        raise ValueError("artifact paths must be unique")
    if paths != sorted(paths):
        raise ValueError("artifact paths must be sorted")
    if contract.as_posix() in paths:
        raise ValueError("artifact contract cannot bind itself")
    unexpected = sorted(set(paths) - ALLOWED_PATHS)
    if unexpected:
        raise ValueError(f"unexpected artifact paths: {', '.join(unexpected)}")

    authorized = _read_decision(decision)
    required = AUTHORIZED_REQUIRED if authorized else DIAGNOSTIC_REQUIRED
    missing_declared = sorted(set(required) - set(paths))
    if missing_declared:
        raise ValueError(f"required artifact paths were not declared: {', '.join(missing_declared)}")

    bindings: list[dict[str, object]] = []
    missing_files: list[str] = []
    for path in files:
        if path.exists() or path.is_symlink():
            _regular_file(path, f"artifact {path.as_posix()}")
            bindings.append(_binding(path))
        elif path.as_posix() in required:
            missing_files.append(path.as_posix())
    if missing_files:
        raise ValueError(f"required artifact files are missing: {', '.join(missing_files)}")

    return {
        "authorization_scope": SCOPE,
        "authorized": authorized,
        "files": bindings,
        "required_paths": list(required),
        "schema_version": 1,
    }


def write_contract(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_contract(path: Path, expected: dict[str, object]) -> None:
    _regular_file(path, "artifact contract")
    try:
        actual = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read artifact contract: {exc}") from exc
    if actual != expected:
        raise ValueError("artifact contract does not match retained evidence")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "verify"))
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--file", action="append", type=Path, default=[], dest="files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = build_contract(decision=args.decision, contract=args.contract, files=args.files)
        if args.mode == "write":
            write_contract(args.contract, payload)
        else:
            verify_contract(args.contract, payload)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        f"{args.mode.upper()}: authorized={str(payload['authorized']).lower()} "
        f"files={len(payload['files'])} {args.contract}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
