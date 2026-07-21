import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_stable_reads", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_payload(path: Path, value: str = "a") -> dict[str, str]:
    payload = {"value": value}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_accepts_unchanged_file(tmp_path):
    path = tmp_path / "stable.json"
    payload = _write_payload(path)

    assert MODULE._read_evidence(path) == payload


def test_handles_short_descriptor_reads(tmp_path, monkeypatch):
    path = tmp_path / "short-reads.json"
    payload = _write_payload(path, "x" * 1_000)
    original_read = MODULE.os.read

    def short_read(descriptor: int, size: int) -> bytes:
        return original_read(descriptor, min(size, 7))

    monkeypatch.setattr(MODULE.os, "read", short_read)

    assert MODULE._read_evidence(path) == payload


def test_rejects_byte_change_between_read_passes(tmp_path, monkeypatch):
    path = tmp_path / "mutated.json"
    _write_payload(path, "a")
    original_lseek = MODULE.os.lseek
    mutated = False

    def mutate_before_second_read(descriptor: int, offset: int, whence: int) -> int:
        nonlocal mutated
        if not mutated:
            mutated = True
            _write_payload(path, "b")
        return original_lseek(descriptor, offset, whence)

    monkeypatch.setattr(MODULE.os, "lseek", mutate_before_second_read)

    with pytest.raises(ValueError, match="changed during reading"):
        MODULE._read_evidence(path)


def test_rejects_metadata_change_with_identical_bytes(tmp_path, monkeypatch):
    path = tmp_path / "metadata-change.json"
    _write_payload(path)
    original_lseek = MODULE.os.lseek
    changed = False

    def touch_before_second_read(descriptor: int, offset: int, whence: int) -> int:
        nonlocal changed
        if not changed:
            changed = True
            metadata = path.stat()
            os.utime(
                path,
                ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1_000_000_000),
            )
        return original_lseek(descriptor, offset, whence)

    monkeypatch.setattr(MODULE.os, "lseek", touch_before_second_read)

    with pytest.raises(ValueError, match="changed during reading"):
        MODULE._read_evidence(path)
