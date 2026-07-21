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
    "validate_release_gate_evidence_special_permissions", SCRIPT
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
def test_accepts_modes_without_special_permission_bits(mode):
    MODULE._validate_file_trust(_metadata(mode))


@pytest.mark.parametrize(
    "special_bit",
    [stat.S_ISUID, stat.S_ISGID, stat.S_ISVTX],
)
def test_rejects_each_special_permission_bit(special_bit):
    with pytest.raises(ValueError, match="special permission bits"):
        MODULE._validate_file_trust(_metadata(0o600 | special_bit))


def test_rejects_combined_special_permission_bits():
    mode = 0o600 | stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX
    with pytest.raises(ValueError, match="special permission bits"):
        MODULE._validate_file_trust(_metadata(mode))


def test_reads_evidence_without_special_permission_bits(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"value": "safe"}), encoding="utf-8")
    path.chmod(0o600)
    assert MODULE._read_evidence(path) == {"value": "safe"}


@pytest.mark.parametrize("special_bit", [stat.S_ISUID, stat.S_ISGID, stat.S_ISVTX])
def test_rejects_evidence_file_with_special_permission_bit(tmp_path, special_bit):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"value": "unsafe"}), encoding="utf-8")
    path.chmod(0o600 | special_bit)
    with pytest.raises(ValueError, match="special permission bits"):
        MODULE._read_evidence(path)


def test_detects_special_permission_change_after_open(tmp_path, monkeypatch):
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
            path.chmod(0o600 | stat.S_ISGID)
            metadata = real_fstat(descriptor)
        return metadata

    monkeypatch.setattr(MODULE.os, "fstat", changing_fstat)
    with pytest.raises(ValueError, match="special permission bits"):
        MODULE._read_evidence(path)
