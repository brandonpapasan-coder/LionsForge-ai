import importlib.util
import sys
import unicodedata
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_combining_mark_boundaries", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    [
        "\u0301",  # nonspacing mark
        "\u093e",  # spacing combining mark
        "\u20dd",  # enclosing mark
    ],
)
def test_rejects_component_beginning_with_combining_mark(character):
    assert unicodedata.category(character) in {"Mn", "Mc", "Me"}
    with pytest.raises(ValueError, match="begin with a Unicode combining mark"):
        MODULE._validate_path_component(f"{character}evidence")


@pytest.mark.parametrize(
    "component",
    [
        "café",
        "किताब",
        "a\u20dd",
        "release-evidence",
    ],
)
def test_accepts_combining_marks_after_base_character(component):
    assert unicodedata.category(component[0]) not in {"Mn", "Mc", "Me"}
    MODULE._validate_path_component(component)


def test_rejects_leading_combining_mark_in_parent_component():
    with pytest.raises(ValueError, match="begin with a Unicode combining mark"):
        MODULE._validate_evidence_path(Path("\u0301artifacts/evidence.json"))


def test_rejects_leading_combining_mark_in_filename():
    with pytest.raises(ValueError, match="begin with a Unicode combining mark"):
        MODULE._validate_evidence_path(Path("\u20ddevidence.json"))


def test_reader_rejects_leading_combining_mark_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="begin with a Unicode combining mark"):
        MODULE._read_evidence(Path("\u0301artifacts/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_leading_combining_mark_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="begin with a Unicode combining mark"):
        MODULE._open_evidence_descriptor(Path("\u20ddevidence.json"))
    assert opened is False
