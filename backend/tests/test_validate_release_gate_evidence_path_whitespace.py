import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_path_whitespace", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("component", [" evidence", "evidence ", " evidence "])
def test_rejects_ascii_space_at_component_edges(component):
    with pytest.raises(ValueError, match="begin or end with a space"):
        MODULE._validate_path_component(component)


def test_accepts_internal_ascii_space():
    MODULE._validate_path_component("release evidence")


@pytest.mark.parametrize(
    "character",
    [
        "\u00a0",  # no-break space
        "\u1680",  # ogham space mark
        "\u2007",  # figure space
        "\u2028",  # line separator
        "\u2029",  # paragraph separator
        "\u205f",  # medium mathematical space
        "\u3000",  # ideographic space
    ],
)
def test_rejects_non_ascii_whitespace(character):
    assert character.isspace()
    with pytest.raises(ValueError, match="non-ASCII whitespace"):
        MODULE._validate_path_component(f"release{character}evidence")


def test_rejects_whitespace_in_parent_component():
    with pytest.raises(ValueError, match="non-ASCII whitespace"):
        MODULE._validate_evidence_path(Path("release\u2028artifacts/evidence.json"))


def test_rejects_leading_space_in_filename():
    with pytest.raises(ValueError, match="begin or end with a space"):
        MODULE._validate_evidence_path(Path(" evidence.json"))


def test_reader_rejects_whitespace_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="non-ASCII whitespace"):
        MODULE._read_evidence(Path("release\u2028artifacts/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_whitespace_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="begin or end with a space"):
        MODULE._open_evidence_descriptor(Path(" evidence.json"))
    assert opened is False
