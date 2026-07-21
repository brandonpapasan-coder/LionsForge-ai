#!/usr/bin/env python3
"""Validate JSON evidence and write it atomically to a regular file."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from pathlib import Path


def validate_destination(path: Path) -> Path:
    if not path.name or path.name in {".", ".."}:
        raise ValueError("output path must name a file")

    parent = path.parent if path.parent != Path("") else Path(".")
    if not parent.exists() or not parent.is_dir():
        raise ValueError("output parent must be an existing directory")
    if parent.is_symlink():
        raise ValueError("output parent must not be a symbolic link")

    if path.exists() or path.is_symlink():
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("output path must not be a symbolic link")
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("output path must be a regular file")

    return parent


def validate_json_document(document: str) -> str:
    try:
        payload = json.loads(document)
    except json.JSONDecodeError as exc:
        raise ValueError("evidence input must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("evidence input must be a JSON object")
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def atomic_write(path: Path, content: str) -> None:
    parent = validate_destination(path)
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
        temporary_path = None
        directory_descriptor = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except OSError as exc:
        raise RuntimeError(f"atomic evidence write failed: {exc}") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rendered = validate_json_document(sys.stdin.read())
        atomic_write(Path(args.output), rendered)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
