import importlib.util
import json
import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_executable", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _metadata(mode: int) -> SimpleNamespace:
    effective_uid = MODULE._effective_uid()
    return SimpleNamespace(
        st_nlink=1,
        st_mode=stat.S_IFREG | mode,
        st_uid=0 if effective_uid is None else effective_uid,
    )


@pytest.mark.parametrize("mode", [0o400, 0o600, 0o640, 0o644])
def test_accepts_non_executable_data_file_modes(mode):
    MODULE._validate_file_trust(_metadata(mode))


@pytest.mark.parametrize(
    "execute_bit",
    [stat.S_IXUSR, stat.S_IXGRP, stat.S_IXOTH],
)
def test_rejects_each_execute_bit(execute_bit):
    with pytest.raises(ValueError, match="must not be executable"):
        MODULE._validate_file_trust(_metadata(0o600 | execute_bit))


def test_rejects_fully_executable_mode():
    with pytest.raises(ValueError, match="must not be executable"):
        MODULE._validate_file_trust(_metadata(0o755))


def test_reads_non_executable_evidence_file(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"value": "safe"}), encoding="utf-8")
    path.chmod(0o600)
    assert MODULE._read_evidence(path) == {"value": "safe"}


def test_rejects_executable_evidence_file(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"value": "unsafe"}), encoding="utf-8")
    path.chmod(0o700)
    with pytest.raises(ValueError, match="must not be executable"):
        MODULE._read_evidence(path)


def test_detects_execute_permission_change_after_open(tmp_path, monkeypatch):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"value": "stable"}), encoding="utf-8")
    path.chmod(0o600)

    real_fstat = os.fstat
    call_count = 0

    def changing_fstat(descriptor):
        nonlocal call_count
        call_count += 1
        metadata = real_fstat(descriptor)
        if call_count == 2:
            path.chmod(0o700)
            metadata = real_fstat(descriptor)
        return metadata

    monkeypatch.setattr(MODULE.os, "fstat", changing_fstat)
    with pytest.raises(ValueError, match="must not be executable"):
        MODULE._read_evidence(path)
