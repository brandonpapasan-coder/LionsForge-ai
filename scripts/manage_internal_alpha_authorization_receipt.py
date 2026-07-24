#!/usr/bin/env python3
"""Write or verify a deterministic Internal Alpha authorization receipt."""

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
HEX_RE = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SCOPE = {
    "external_staging_proven": False,
    "public_access_authorized": False,
    "repository_only": True,
}


def _read_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _exact_keys(value: dict, expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keys are invalid")


def _regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.exists() or not path.is_file():
        raise ValueError(f"{label} is missing, symlinked, or not regular")


def _binding(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"path": path.as_posix(), "sha256": digest.hexdigest(), "size_bytes": size}


def _validate_manifest(manifest: dict) -> tuple[str, str, str, str]:
    _exact_keys(
        manifest,
        {"authorization_scope", "candidate", "gates", "provenance", "schema_version"},
        "manifest",
    )
    if manifest["schema_version"] != 1 or isinstance(manifest["schema_version"], bool):
        raise ValueError("manifest schema_version must be 1")
    if manifest["authorization_scope"] != SCOPE:
        raise ValueError("manifest weakens repository-only boundaries")
    provenance = manifest["provenance"]
    candidate = manifest["candidate"]
    if not isinstance(provenance, dict) or not isinstance(candidate, dict):
        raise ValueError("manifest provenance and candidate must be objects")
    repository = provenance.get("repository")
    candidate_sha = candidate.get("candidate_sha")
    backend_digest = candidate.get("backend_digest")
    frontend_digest = candidate.get("frontend_digest")
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("manifest repository is invalid")
    for value, pattern, label in (
        (candidate_sha, SHA_RE, "candidate SHA"),
        (backend_digest, DIGEST_RE, "backend digest"),
        (frontend_digest, DIGEST_RE, "frontend digest"),
    ):
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise ValueError(f"manifest {label} is invalid")
    return repository, candidate_sha, backend_digest, frontend_digest


def _validate_inventory(inventory: dict) -> int:
    _exact_keys(inventory, {"files", "schema_version"}, "inventory")
    if inventory["schema_version"] != 1 or isinstance(inventory["schema_version"], bool):
        raise ValueError("inventory schema_version must be 1")
    files = inventory["files"]
    if not isinstance(files, list) or not files:
        raise ValueError("inventory files must be a non-empty list")
    paths: list[str] = []
    for index, raw in enumerate(files):
        if not isinstance(raw, dict):
            raise ValueError(f"inventory files[{index}] must be an object")
        _exact_keys(raw, {"path", "sha256", "size_bytes"}, f"inventory files[{index}]")
        path = raw["path"]
        digest = raw["sha256"]
        size = raw["size_bytes"]
        if not isinstance(path, str) or not path:
            raise ValueError(f"inventory files[{index}].path is invalid")
        if not isinstance(digest, str) or not HEX_RE.fullmatch(digest):
            raise ValueError(f"inventory files[{index}].sha256 is invalid")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"inventory files[{index}].size_bytes is invalid")
        paths.append(path)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("inventory paths must be unique and sorted")
    return len(files)


def build_receipt(manifest_path: Path, inventory_path: Path, receipt_path: Path) -> dict[str, object]:
    for path, label in ((manifest_path, "manifest"), (inventory_path, "inventory")):
        _regular_file(path, label)
        if path.resolve(strict=False) == receipt_path.resolve(strict=False):
            raise ValueError("receipt cannot bind itself")
    manifest = _read_json(manifest_path, "manifest")
    inventory = _read_json(inventory_path, "inventory")
    repository, candidate_sha, backend_digest, frontend_digest = _validate_manifest(manifest)
    file_count = _validate_inventory(inventory)
    return {
        "authorization_scope": SCOPE,
        "bindings": {
            "inventory": _binding(inventory_path),
            "inventory_file_count": file_count,
            "manifest": _binding(manifest_path),
        },
        "candidate": {
            "backend_digest": backend_digest,
            "candidate_sha": candidate_sha,
            "frontend_digest": frontend_digest,
            "repository": repository,
        },
        "schema_version": 1,
    }


def write_receipt(manifest: Path, inventory: Path, receipt: Path) -> None:
    payload = build_receipt(manifest, inventory, receipt)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt.with_name(f".{receipt.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(receipt)


def verify_receipt(manifest: Path, inventory: Path, receipt: Path) -> None:
    _regular_file(receipt, "receipt")
    actual = _read_json(receipt, "receipt")
    expected = build_receipt(manifest, inventory, receipt)
    if actual != expected:
        raise ValueError("authorization receipt does not match bound evidence")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "verify"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.mode == "write":
            write_receipt(args.manifest, args.inventory, args.receipt)
        else:
            verify_receipt(args.manifest, args.inventory, args.receipt)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"{args.mode.upper()}: {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
