import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_unicode_noncharacters", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    [
        "\ufdd0",
        "\ufdef",
        "\ufffe",
        "\uffff",
        "\U0001fffe",
        "\U0001ffff",
        "\U0010fffe",
        "\U0010ffff",
    ],
)
def test_rejects_unicode_noncharacters(character):
    with pytest.raises(ValueError, match="Unicode noncharacters"):
        MODULE._validate_path_component(f"release{character}evidence")


@pytest.mark.parametrize(
    "component",
    [
        "release-evidence",
        "café",
        "資料",
        "emoji-😀",
        "supplementary-𐐷",
    ],
)
def test_accepts_valid_unicode_scalars(component):
    MODULE._validate_path_component(component)


def test_rejects_noncharacter_in_parent_component():
    with pytest.raises(ValueError, match="Unicode noncharacters"):
        MODULE._validate_evidence_path(Path("artifacts\ufdd0/evidence.json"))


def test_rejects_noncharacter_in_filename():
    with pytest.raises(ValueError, match="Unicode noncharacters"):
        MODULE._validate_evidence_path(Path("evidence\U0001ffff.json"))


def test_reader_rejects_noncharacter_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="Unicode noncharacters"):
        MODULE._read_evidence(Path("artifacts\ufdd0/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_noncharacter_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="Unicode noncharacters"):
        MODULE._open_evidence_descriptor(Path("evidence\U0010ffff.json"))
    assert opened is False
