import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_filesystems", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_evidence(path: Path, value: str = "safe") -> None:
    path.write_text(json.dumps({"value": value}), encoding="utf-8")
    path.chmod(0o600)


def test_reads_evidence_from_ordinary_filesystem(tmp_path):
    path = tmp_path / "evidence.json"
    _write_evidence(path)
    assert MODULE._read_evidence(path) == {"value": "safe"}


@pytest.mark.skipif(os.name != "posix", reason="POSIX virtual roots are not applicable")
@pytest.mark.parametrize(
    "path",
    [Path("/proc/evidence.json"), Path("/sys/evidence.json"), Path("/dev/evidence.json")],
)
def test_rejects_known_virtual_filesystem_roots(path):
    with pytest.raises(ValueError, match="virtual filesystem"):
        MODULE._validate_filesystem_path(path)


def test_non_posix_platform_skips_virtual_root_rule(monkeypatch):
    monkeypatch.setattr(MODULE._CORE, "os", SimpleNamespace(name="nt"))
    MODULE._validate_filesystem_path(Path("/proc/evidence.json"))


def test_filesystem_identity_returns_none_without_fstatvfs(monkeypatch):
    monkeypatch.delattr(MODULE.os, "fstatvfs", raising=False)
    assert MODULE._filesystem_identity(123) is None


def test_filesystem_inspection_failure_is_rejected(monkeypatch):
    def failing_fstatvfs(descriptor):
        raise OSError("inspection failed")

    monkeypatch.setattr(MODULE.os, "fstatvfs", failing_fstatvfs, raising=False)
    with pytest.raises(ValueError, match="unable to inspect evidence filesystem"):
        MODULE._filesystem_identity(123)


def test_identity_uses_stable_fields_not_free_space_counters(monkeypatch):
    values = iter(
        [
            SimpleNamespace(
                f_fsid=7,
                f_bsize=4096,
                f_frsize=4096,
                f_blocks=1000,
                f_bfree=900,
                f_bavail=850,
                f_files=100,
                f_ffree=90,
                f_favail=80,
                f_flag=0,
                f_namemax=255,
            ),
            SimpleNamespace(
                f_fsid=7,
                f_bsize=4096,
                f_frsize=4096,
                f_blocks=1000,
                f_bfree=800,
                f_bavail=750,
                f_files=100,
                f_ffree=70,
                f_favail=60,
                f_flag=0,
                f_namemax=255,
            ),
        ]
    )
    monkeypatch.setattr(MODULE.os, "fstatvfs", lambda descriptor: next(values), raising=False)
    assert MODULE._filesystem_identity(1) == MODULE._filesystem_identity(1)


def test_detects_filesystem_identity_change_during_read(tmp_path, monkeypatch):
    path = tmp_path / "evidence.json"
    _write_evidence(path)
    identities = iter([(1,), (2,), (2,)])
    monkeypatch.setattr(MODULE, "_filesystem_identity", lambda descriptor: next(identities))

    with pytest.raises(ValueError, match="filesystem changed during reading"):
        MODULE._read_evidence(path)
