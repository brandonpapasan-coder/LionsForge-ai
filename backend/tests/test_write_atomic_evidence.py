import importlib.util
import os
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "write_atomic_evidence.py"
SPEC = importlib.util.spec_from_file_location("write_atomic_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_validate_json_document_requires_object_and_normalizes():
    rendered = MODULE.validate_json_document('{"b": 2, "a": 1}')
    assert rendered == '{\n  "a": 1,\n  "b": 2\n}\n'

    with pytest.raises(ValueError, match="valid JSON"):
        MODULE.validate_json_document("{")

    with pytest.raises(ValueError, match="JSON object"):
        MODULE.validate_json_document("[]")


def test_atomic_write_creates_and_replaces_regular_file(tmp_path):
    output = tmp_path / "evidence.json"
    MODULE.atomic_write(output, '{"passed": false}\n')
    assert output.read_text(encoding="utf-8") == '{"passed": false}\n'
    assert output.stat().st_mode & 0o777 == 0o600

    MODULE.atomic_write(output, '{"passed": true}\n')
    assert output.read_text(encoding="utf-8") == '{"passed": true}\n'
    assert list(tmp_path.glob(".evidence.json.*.tmp")) == []


def test_validate_destination_rejects_missing_parent_and_directory(tmp_path):
    with pytest.raises(ValueError, match="existing directory"):
        MODULE.validate_destination(tmp_path / "missing" / "evidence.json")

    directory_target = tmp_path / "directory-target"
    directory_target.mkdir()
    with pytest.raises(ValueError, match="regular file"):
        MODULE.validate_destination(directory_target)


def test_validate_destination_rejects_symlink_target(tmp_path):
    real_target = tmp_path / "real.json"
    real_target.write_text("{}\n", encoding="utf-8")
    link_target = tmp_path / "linked.json"
    link_target.symlink_to(real_target)

    with pytest.raises(ValueError, match="symbolic link"):
        MODULE.validate_destination(link_target)


def test_validate_destination_rejects_symlink_parent(tmp_path):
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(ValueError, match="parent must not be a symbolic link"):
        MODULE.validate_destination(linked_parent / "evidence.json")


def test_atomic_write_reports_os_error_and_cleans_temp_file(tmp_path, monkeypatch):
    output = tmp_path / "evidence.json"

    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr(MODULE.os, "replace", fail_replace)

    with pytest.raises(RuntimeError, match="atomic evidence write failed"):
        MODULE.atomic_write(output, "{}\n")

    assert not output.exists()
    assert list(tmp_path.glob(".evidence.json.*.tmp")) == []


def test_main_returns_controlled_error_for_invalid_input(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(MODULE.sys, "stdin", type("Input", (), {"read": lambda self: "[]"})())
    monkeypatch.setattr(
        MODULE,
        "parse_args",
        lambda: type("Args", (), {"output": str(tmp_path / "evidence.json")})(),
    )

    assert MODULE.main() == 2
    assert "ERROR: evidence input must be a JSON object" in capsys.readouterr().err
