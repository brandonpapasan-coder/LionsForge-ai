#!/usr/bin/env python3
"""Validate persisted release-gate evidence independently of the API verifier."""

from __future__ import annotations

import importlib.util
import inspect
import stat
import sys
import unicodedata
from pathlib import Path
from types import ModuleType

_CORE_PATH = Path(__file__).with_name("validate_release_gate_evidence_core.py")
_CORE_SPEC = importlib.util.spec_from_file_location(
    "_lionsforge_release_gate_evidence_core", _CORE_PATH
)
if _CORE_SPEC is None or _CORE_SPEC.loader is None:
    raise ImportError(f"unable to load release-gate validator core from {_CORE_PATH}")
_CORE = importlib.util.module_from_spec(_CORE_SPEC)
sys.modules[_CORE_SPEC.name] = _CORE
_CORE_SPEC.loader.exec_module(_CORE)


def _validate_json_string(value: str) -> None:
    if len(value) > _CORE.MAX_JSON_STRING_CHARACTERS:
        raise ValueError(
            "evidence JSON string exceeds the maximum character count of "
            f"{_CORE.MAX_JSON_STRING_CHARACTERS}"
        )
    if _CORE._contains_surrogate(value):
        raise ValueError("evidence JSON contains an invalid Unicode surrogate")
    if _CORE._contains_unicode_noncharacter(value):
        raise ValueError("evidence JSON contains a Unicode noncharacter")
    if _CORE._contains_format_character(value):
        raise ValueError("evidence JSON contains a Unicode format character")
    if _CORE._contains_unstable_unicode_assignment(value):
        raise ValueError("evidence JSON contains private-use or unassigned Unicode characters")
    if _CORE._contains_unicode_variation_selector(value):
        raise ValueError("evidence JSON contains a Unicode variation selector")
    if _CORE._contains_control_character(value):
        raise ValueError("evidence JSON contains a control character")


_ORIGINAL_VALIDATE_PATH_COMPONENT = _CORE._validate_path_component
_ORIGINAL_READ_EVIDENCE = _CORE._read_evidence


def _validate_path_component(component: str) -> None:
    """Preserve specific Unicode and ambiguity diagnostics before generic checks."""
    if _CORE._contains_unicode_tag_character(component):
        raise ValueError("evidence path components must not contain Unicode tag characters")
    if _CORE._contains_non_ascii_whitespace(component):
        raise ValueError("evidence path components must not contain non-ASCII whitespace")
    if _CORE._contains_non_ascii_decimal_digit(component):
        raise ValueError("evidence path components must use ASCII decimal digits")
    if any(unicodedata.normalize("NFKC", character) != character for character in component):
        raise ValueError("evidence path components must not use Unicode compatibility forms")
    try:
        _ORIGINAL_VALIDATE_PATH_COMPONENT(component)
    except ValueError as exc:
        message = str(exc)
        if message in {
            "evidence path components must not begin or end with a space",
            "evidence path components must not end with a dot",
        }:
            raise ValueError(
                "evidence path components must not begin or end with a space or dot"
            ) from exc
        raise


def _descriptor_relative_open_supported() -> bool:
    """Use descriptor traversal only when the active os.open accepts dir_fd."""
    if not (
        hasattr(_CORE.os, "O_DIRECTORY")
        and hasattr(_CORE.os, "O_NOFOLLOW")
        and _CORE.os.open in getattr(_CORE.os, "supports_dir_fd", set())
    ):
        return False
    try:
        signature = inspect.signature(_CORE.os.open)
    except (TypeError, ValueError):
        return True
    return "dir_fd" in signature.parameters or any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def _read_evidence(path: Path) -> object:
    """Retain precise compatibility diagnostics around the hardened reader."""
    if path.suffix and path.suffix != ".json":
        raise ValueError("evidence filename must use the lowercase .json suffix")
    try:
        return _ORIGINAL_READ_EVIDENCE(path)
    except ValueError as exc:
        message = str(exc)
        if message == "evidence filename must use the lowercase .json suffix":
            try:
                metadata = path.lstat()
            except OSError:
                raise
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError("evidence file must not be a symbolic link") from exc
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("evidence file must be a regular file") from exc
        if message == "evidence file changed during reading":
            raise ValueError(
                "evidence file changed during reading or was truncated during reading"
            ) from exc
        raise


setattr(_CORE, "_validate_json_string", _validate_json_string)
setattr(_CORE, "_validate_path_component", _validate_path_component)
setattr(_CORE, "_descriptor_relative_open_supported", _descriptor_relative_open_supported)
setattr(_CORE, "_read_evidence", _read_evidence)

for _name in dir(_CORE):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_CORE, _name)
globals()["_validate_json_string"] = _validate_json_string
globals()["_validate_path_component"] = _validate_path_component
globals()["_descriptor_relative_open_supported"] = _descriptor_relative_open_supported
globals()["_read_evidence"] = _read_evidence


class _CoreProxyModule(ModuleType):
    """Keep public-module monkeypatches synchronized with the loaded core."""

    def __setattr__(self, name: str, value: object) -> None:
        if name not in {"_CORE", "__class__"} and not name.startswith("__"):
            setattr(_CORE, name, value)
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        if name not in {"_CORE", "__class__"} and not name.startswith("__"):
            if hasattr(_CORE, name):
                delattr(_CORE, name)
        super().__delattr__(name)


sys.modules[__name__].__class__ = _CoreProxyModule


if __name__ == "__main__":
    raise SystemExit(_CORE.main())
