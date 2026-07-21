import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_release_gate_evidence_file_trust", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path) -> None:
    path.write_text(json.dumps({"value": "stable"}), encoding="utf-8")


def test_accepts_owner_writable_file(tmp_path):
    path = tmp_path / "owner-writable.json"
    _write_json(path)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    assert MODULE._read_evidence(path) == {"value": "stable"}


def test_accepts_owner_writable_world_readable_file(tmp_path):
    path = tmp_path / "ordinary.json"
    _write_json(path)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    assert MODULE._read_evidence(path) == {"value": "stable"}


@pytest.mark.parametrize("write_bit", [stat.S_IWGRP, stat.S_IWOTH])
def test_rejects_untrusted_write_permissions(tmp_path, write_bit):
    path = tmp_path / "untrusted-writable.json"
    _write_json(path)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR | write_bit)

    with pytest.raises(ValueError, match="group- or world-writable"):
        MODULE._read_evidence(path)


def test_rejects_multiple_hard_links(tmp_path):
    path = tmp_path / "evidence.json"
    linked = tmp_path / "alternate.json"
    _write_json(path)
    try:
        os.link(path, linked)
    except OSError as exc:
        pytest.skip(f"hard links are not supported in this environment: {exc}")

    with pytest.raises(ValueError, match="multiple hard links"):
        MODULE._read_evidence(path)


def test_rejects_permission_change_after_open(tmp_path, monkeypatch):
    path = tmp_path / "permission-change.json"
    _write_json(path)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    real_fstat = MODULE.os.fstat
    calls = 0

    def changing_fstat(descriptor):
        nonlocal calls
        metadata = real_fstat(descriptor)
        calls += 1
        if calls == 2:
            path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IWGRP)
            metadata = real_fstat(descriptor)
        return metadata

    monkeypatch.setattr(MODULE.os, "fstat", changing_fstat)

    with pytest.raises(ValueError, match="group- or world-writable"):
        MODULE._read_evidence(path)
