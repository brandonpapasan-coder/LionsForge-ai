import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_descriptor_traversal", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_evidence(path: Path, value: str = "safe") -> None:
    path.write_text(json.dumps({"value": value}), encoding="utf-8")
    path.chmod(0o600)


def test_reads_nested_file_with_descriptor_relative_traversal(tmp_path):
    nested = tmp_path / "one" / "two"
    nested.mkdir(parents=True)
    path = nested / "evidence.json"
    _write_evidence(path)
    assert MODULE._read_evidence(path) == {"value": "safe"}


def test_descriptor_relative_open_uses_directory_and_nofollow_flags(tmp_path, monkeypatch):
    if not MODULE._descriptor_relative_open_supported():
        pytest.skip("descriptor-relative opening is unavailable")

    nested = tmp_path / "one"
    nested.mkdir()
    path = nested / "evidence.json"
    _write_evidence(path)

    real_open = os.open
    calls = []

    def recording_open(target, flags, *args, **kwargs):
        calls.append((target, flags, kwargs.get("dir_fd")))
        return real_open(target, flags, *args, **kwargs)

    monkeypatch.setattr(MODULE.os, "open", recording_open)
    descriptor = MODULE._open_evidence_descriptor(path)
    os.close(descriptor)

    parent_calls = [call for call in calls[:-1]]
    assert parent_calls
    assert all(flags & os.O_DIRECTORY for _, flags, _ in parent_calls)
    assert all(flags & os.O_NOFOLLOW for _, flags, _ in parent_calls)
    assert any(dir_fd is not None for _, _, dir_fd in parent_calls[1:])
    assert calls[-1][1] & os.O_NOFOLLOW
    assert calls[-1][2] is not None


def test_descriptor_traversal_rejects_symlink_parent_without_precheck(tmp_path, monkeypatch):
    if not MODULE._descriptor_relative_open_supported():
        pytest.skip("descriptor-relative opening is unavailable")

    target = tmp_path / "target"
    target.mkdir()
    path = target / "evidence.json"
    _write_evidence(path)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are unavailable")

    monkeypatch.setattr(MODULE, "_validate_parent_components", lambda value: None)
    with pytest.raises(ValueError, match="unable to open evidence file safely"):
        MODULE._read_evidence(alias / "evidence.json")


def test_fallback_open_remains_available(tmp_path, monkeypatch):
    path = tmp_path / "evidence.json"
    _write_evidence(path)
    monkeypatch.setattr(MODULE, "_descriptor_relative_open_supported", lambda: False)

    descriptor = MODULE._open_evidence_descriptor(path)
    try:
        metadata = os.fstat(descriptor)
        assert stat.S_ISREG(metadata.st_mode)
    finally:
        os.close(descriptor)


def test_descriptor_traversal_rejects_symlink_final_component(tmp_path):
    if not MODULE._descriptor_relative_open_supported():
        pytest.skip("descriptor-relative opening is unavailable")

    target = tmp_path / "target.json"
    _write_evidence(target)
    alias = tmp_path / "alias.json"
    try:
        alias.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("file symlinks are unavailable")

    with pytest.raises(ValueError, match="unable to open evidence file safely"):
        MODULE._open_evidence_descriptor(alias)
