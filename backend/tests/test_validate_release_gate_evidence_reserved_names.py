import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_reserved_names", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "component",
    [
        "CON",
        "con.json",
        "PrN.txt",
        "aux.data",
        "NUL",
        "COM1",
        "com9.log",
        "LPT1",
        "lpt9.json",
    ],
)
def test_rejects_reserved_device_names_case_insensitively(component):
    with pytest.raises(ValueError, match="reserved device names"):
        MODULE._validate_path_component(component)


@pytest.mark.parametrize(
    "component",
    [
        "console",
        "null",
        "auxiliary",
        "COM0",
        "COM10",
        "LPT0",
        "LPT10",
        "com1-port",
        "lpt1_backup",
    ],
)
def test_accepts_safe_near_matches(component):
    MODULE._validate_path_component(component)


def test_rejects_reserved_parent_component():
    with pytest.raises(ValueError, match="reserved device names"):
        MODULE._validate_evidence_path(Path("con/evidence.json"))


def test_rejects_reserved_filename_stem_with_json_suffix():
    with pytest.raises(ValueError, match="reserved device names"):
        MODULE._validate_evidence_path(Path("NUL.json"))


def test_reader_rejects_reserved_name_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="reserved device names"):
        MODULE._read_evidence(Path("con/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_reserved_name_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="reserved device names"):
        MODULE._open_evidence_descriptor(Path("NUL.json"))
    assert opened is False
