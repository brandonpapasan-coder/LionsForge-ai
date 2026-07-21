import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_release_gate_evidence_ownership", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _metadata(*, uid: int, mode: int = 0o100600, nlink: int = 1):
    return SimpleNamespace(st_uid=uid, st_mode=mode, st_nlink=nlink)


def test_accepts_file_owned_by_effective_user(monkeypatch):
    monkeypatch.setattr(MODULE, "_effective_uid", lambda: 1234)
    MODULE._validate_file_trust(_metadata(uid=1234))


def test_rejects_file_owned_by_another_user(monkeypatch):
    monkeypatch.setattr(MODULE, "_effective_uid", lambda: 1234)
    with pytest.raises(ValueError, match="owned by the effective user"):
        MODULE._validate_file_trust(_metadata(uid=5678))


def test_skips_owner_check_when_platform_has_no_effective_uid(monkeypatch):
    monkeypatch.setattr(MODULE, "_effective_uid", lambda: None)
    MODULE._validate_file_trust(_metadata(uid=5678))


def test_reads_normally_owned_file(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"value": "stable"}), encoding="utf-8")
    path.chmod(0o600)
    assert MODULE._read_evidence(path) == {"value": "stable"}


def test_rejects_ownership_change_after_open(monkeypatch, tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"value": "stable"}), encoding="utf-8")
    path.chmod(0o600)

    actual_fstat = MODULE.os.fstat
    calls = 0

    def changing_fstat(descriptor):
        nonlocal calls
        calls += 1
        metadata = actual_fstat(descriptor)
        if calls < 2:
            return metadata
        values = list(metadata)
        values[4] = metadata.st_uid + 1
        return os.stat_result(values)

    monkeypatch.setattr(MODULE.os, "fstat", changing_fstat)
    with pytest.raises(ValueError, match="owned by the effective user"):
        MODULE._read_evidence(path)
