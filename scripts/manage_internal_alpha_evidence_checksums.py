#!/usr/bin/env python3
"""Write or verify a deterministic Internal Alpha evidence checksum inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

SCHEMA_VERSION = 1


def _validate_paths(paths: list[Path], inventory: Path) -> list[Path]:
    normalized: list[Path] = []
    seen: set[str] = set()
    inventory_resolved = inventory.resolve(strict=False)
    for path in paths:
        text = path.as_posix()
        if text in seen:
            raise ValueError(f"duplicate evidence path: {text}")
        seen.add(text)
        if path.resolve(strict=False) == inventory_resolved:
            raise ValueError("inventory cannot checksum itself")
        if path.is_symlink():
            raise ValueError(f"symlinks are not allowed: {text}")
        if not path.exists() or not path.is_file():
            raise ValueError(f"evidence file is missing or not regular: {text}")
        normalized.append(path)
    if not normalized:
        raise ValueError("at least one evidence file is required")
    return sorted(normalized, key=lambda item: item.as_posix())


def _entry(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"path": path.as_posix(), "sha256": digest.hexdigest(), "size_bytes": size}


def build_inventory(paths: list[Path], inventory: Path) -> dict[str, object]:
    validated = _validate_paths(paths, inventory)
    return {"schema_version": SCHEMA_VERSION, "files": [_entry(path) for path in validated]}


def write_inventory(paths: list[Path], inventory: Path) -> None:
    payload = build_inventory(paths, inventory)
    inventory.parent.mkdir(parents=True, exist_ok=True)
    temporary = inventory.with_name(f".{inventory.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(inventory)


def verify_inventory(paths: list[Path], inventory: Path) -> None:
    try:
        payload = json.loads(inventory.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read inventory: {exc}") from exc
    expected = build_inventory(paths, inventory)
    if payload != expected:
        raise ValueError("checksum inventory does not match evidence files")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "verify"))
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("files", nargs="+", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.mode == "write":
            write_inventory(args.files, args.inventory)
        else:
            verify_inventory(args.files, args.inventory)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"{args.mode.upper()}: {args.inventory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
