#!/usr/bin/env python3
"""Validate persisted release-gate evidence independently of the API verifier."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path

REQUIRED_WORKFLOW_PATHS = {
    "Backend CI": ".github/workflows/backend-ci.yml",
    "Frontend CI": ".github/workflows/frontend-ci.yml",
    "Security Gate": ".github/workflows/security-gate.yml",
    "Deployment Validation": ".github/workflows/deployment-validation.yml",
}
REQUIRED_EVENT = "push"
REQUIRED_BRANCH = "main"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_EVIDENCE_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 10_000
MAX_JSON_INTEGER_DIGITS = 20
MAX_JSON_STRING_CHARACTERS = 4_096
MAX_PATH_COMPONENT_BYTES = 255
MAX_PATH_BYTES = 4_096
MAX_PATH_COMPONENTS = 64
UNTRUSTED_WRITE_BITS = stat.S_IWGRP | stat.S_IWOTH
EXECUTE_BITS = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
SPECIAL_PERMISSION_BITS = stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX
VIRTUAL_FILESYSTEM_ROOTS = (Path("/proc"), Path("/sys"), Path("/dev"))
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
PORTABLE_FORBIDDEN_PATH_CHARACTERS = frozenset('<>:"/\\|?*')
ALLOWED_STATUSES = {
    "completed", "in_progress", "pending", "queued", "requested", "waiting"
}
ALLOWED_CONCLUSIONS = {
    "action_required", "cancelled", "failure", "neutral", "skipped", "stale",
    "startup_failure", "success", "timed_out",
}
TOP_LEVEL_KEYS = {
    "repository", "release_sha", "required_event", "required_branch",
    "required_workflow_paths", "passed", "gates",
}
GATE_KEYS = {
    "name", "path", "status", "conclusion", "run_id", "html_url", "event",
    "head_branch", "head_sha",
}


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"evidence JSON contains duplicate key: {key}")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> object:
    raise ValueError(f"evidence JSON contains non-standard constant: {value}")


def _parse_bounded_integer(value: str) -> int:
    digits = value[1:] if value.startswith("-") else value
    if len(digits) > MAX_JSON_INTEGER_DIGITS:
        raise ValueError(
            "evidence JSON integer exceeds the maximum digit count of "
            f"{MAX_JSON_INTEGER_DIGITS}"
        )
    return int(value)


def _reject_float(value: str) -> object:
    raise ValueError(f"evidence JSON contains unsupported floating-point value: {value}")


def _contains_surrogate(value: str) -> bool:
    return any(0xD800 <= ord(character) <= 0xDFFF for character in value)


def _contains_control_character(value: str) -> bool:
    return any(
        ord(character) < 0x20 or 0x7F <= ord(character) <= 0x9F
        for character in value
    )


def _validate_json_string(value: str) -> None:
    if len(value) > MAX_JSON_STRING_CHARACTERS:
        raise ValueError(
            "evidence JSON string exceeds the maximum character count of "
            f"{MAX_JSON_STRING_CHARACTERS}"
        )
    if _contains_surrogate(value):
        raise ValueError("evidence JSON contains an invalid Unicode surrogate")
    if _contains_control_character(value):
        raise ValueError("evidence JSON contains a control character")


def _validate_json_tree(value: object) -> None:
    stack: list[tuple[object, int]] = [(value, 1)]
    node_count = 0
    while stack:
        current, depth = stack.pop()
        node_count += 1
        if node_count > MAX_JSON_NODES:
            raise ValueError(
                f"evidence JSON exceeds the maximum node count of {MAX_JSON_NODES}"
            )
        if depth > MAX_JSON_DEPTH:
            raise ValueError(
                f"evidence JSON exceeds the maximum nesting depth of {MAX_JSON_DEPTH}"
            )
        if isinstance(current, str):
            _validate_json_string(current)
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
        elif isinstance(current, dict):
            for key, item in current.items():
                node_count += 1
                if node_count > MAX_JSON_NODES:
                    raise ValueError(
                        f"evidence JSON exceeds the maximum node count of {MAX_JSON_NODES}"
                    )
                _validate_json_string(key)
                stack.append((item, depth + 1))


def _validate_unicode_scalars(value: object) -> None:
    """Compatibility wrapper retained for direct unit tests."""
    _validate_json_tree(value)


def _file_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        metadata.st_uid,
        metadata.st_mode,
    )


def _effective_uid() -> int | None:
    getter = getattr(os, "geteuid", None)
    return getter() if getter is not None else None


def _validate_file_trust(metadata: os.stat_result) -> None:
    if metadata.st_nlink != 1:
        raise ValueError("evidence file must not have multiple hard links")
    if metadata.st_mode & UNTRUSTED_WRITE_BITS:
        raise ValueError("evidence file must not be group- or world-writable")
    if metadata.st_mode & EXECUTE_BITS:
        raise ValueError("evidence file must not be executable")
    if metadata.st_mode & SPECIAL_PERMISSION_BITS:
        raise ValueError("evidence file must not have special permission bits")
    effective_uid = _effective_uid()
    if effective_uid is not None and metadata.st_uid != effective_uid:
        raise ValueError("evidence file must be owned by the effective user")


def _validate_path_component(component: str) -> None:
    if _contains_surrogate(component):
        raise ValueError("evidence path components must contain valid Unicode scalars")
    if _contains_control_character(component):
        raise ValueError("evidence path components must not contain control characters")
    if unicodedata.normalize("NFC", component) != component:
        raise ValueError("evidence path components must use NFC Unicode normalization")
    if any(character in PORTABLE_FORBIDDEN_PATH_CHARACTERS for character in component):
        raise ValueError("evidence path components contain a forbidden portable character")
    if component.endswith((" ", ".")):
        raise ValueError("evidence path components must not end with a space or dot")
    if len(component.encode("utf-8")) > MAX_PATH_COMPONENT_BYTES:
        raise ValueError(
            "evidence path component exceeds the maximum UTF-8 byte length of "
            f"{MAX_PATH_COMPONENT_BYTES}"
        )
    reserved_stem = component.split(".", 1)[0].upper()
    if reserved_stem in WINDOWS_RESERVED_NAMES:
        raise ValueError("evidence path components must not use reserved device names")


def _validate_evidence_path(path: Path) -> None:
    name = path.name
    if not name:
        raise ValueError("evidence path must identify a file")
    if ".." in path.parts:
        raise ValueError("evidence path must not contain parent traversal components")
    try:
        encoded_path = os.fspath(path).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("evidence path must contain valid Unicode scalars") from exc
    if len(encoded_path) > MAX_PATH_BYTES:
        raise ValueError(
            "evidence path exceeds the maximum UTF-8 byte length of "
            f"{MAX_PATH_BYTES}"
        )
    anchor = path.anchor
    components = tuple(component for component in path.parts if component != anchor)
    if len(components) > MAX_PATH_COMPONENTS:
        raise ValueError(
            "evidence path exceeds the maximum component count of "
            f"{MAX_PATH_COMPONENTS}"
        )
    for component in components:
        _validate_path_component(component)
    if name.startswith("."):
        raise ValueError("evidence filename must not be hidden")
    if name.startswith("-"):
        raise ValueError("evidence filename must not begin with a hyphen")
    if path.suffix != ".json":
        raise ValueError("evidence filename must use the lowercase .json suffix")


def _validate_filesystem_path(path: Path) -> None:
    if os.name != "posix":
        return
    absolute = path.absolute()
    for root in VIRTUAL_FILESYSTEM_ROOTS:
        if absolute == root or root in absolute.parents:
            raise ValueError("evidence file must not reside on a virtual filesystem")


def _filesystem_identity(descriptor: int) -> tuple[int, ...] | None:
    getter = getattr(os, "fstatvfs", None)
    if getter is None:
        return None
    try:
        metadata = getter(descriptor)
    except OSError as exc:
        raise ValueError(f"unable to inspect evidence filesystem: {exc}") from exc
    fields = (
        "f_bsize", "f_frsize", "f_blocks", "f_files", "f_flag", "f_namemax",
    )
    identity = tuple(int(getattr(metadata, field)) for field in fields)
    fsid = getattr(metadata, "f_fsid", None)
    return identity if fsid is None else (int(fsid), *identity)


def _validate_parent_components(path: Path) -> None:
    _validate_evidence_path(path)
    absolute = path.absolute()
    parent = absolute.parent
    anchor = Path(parent.anchor)
    current = anchor
    parts = parent.parts[1:] if parent.anchor else parent.parts
    for component in parts:
        current = current / component
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise ValueError(f"unable to inspect evidence parent path: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("evidence parent path must not contain symbolic links")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("evidence parent path components must be directories")


def _descriptor_relative_open_supported() -> bool:
    return (
        hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and os.open in getattr(os, "supports_dir_fd", set())
    )


def _open_evidence_descriptor(path: Path) -> int:
    _validate_evidence_path(path)
    _validate_filesystem_path(path)
    file_flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        file_flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        file_flags |= os.O_NOFOLLOW

    if not _descriptor_relative_open_supported():
        try:
            return os.open(path, file_flags)
        except OSError as exc:
            raise ValueError(f"unable to open evidence file safely: {exc}") from exc

    absolute = path.absolute()
    parts = absolute.parts
    if not parts or not absolute.anchor:
        raise ValueError("unable to open evidence file safely: path has no absolute anchor")

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC

    directory_descriptor: int | None = None
    try:
        directory_descriptor = os.open(absolute.anchor, directory_flags)
        for component in parts[1:-1]:
            next_descriptor = os.open(
                component,
                directory_flags,
                dir_fd=directory_descriptor,
            )
            metadata = os.fstat(next_descriptor)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(next_descriptor)
                raise ValueError("evidence parent path components must be directories")
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        return os.open(parts[-1], file_flags, dir_fd=directory_descriptor)
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError(f"unable to open evidence file safely: {exc}") from exc
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def _read_bounded_descriptor(descriptor: int) -> bytes:
    chunks: list[bytes] = []
    remaining = MAX_EVIDENCE_BYTES + 1
    while remaining > 0:
        chunk = os.read(descriptor, min(64 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_evidence(path: Path) -> object:
    _validate_evidence_path(path)
    _validate_filesystem_path(path)
    _validate_parent_components(path)
    try:
        before = path.lstat()
    except OSError as exc:
        raise ValueError(f"unable to inspect evidence file: {exc}") from exc
    if stat.S_ISLNK(before.st_mode):
        raise ValueError("evidence file must not be a symbolic link")
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("evidence file must be a regular file")
    _validate_file_trust(before)
    if before.st_size <= 0:
        raise ValueError("evidence file must not be empty")
    if before.st_size > MAX_EVIDENCE_BYTES:
        raise ValueError(
            f"evidence file exceeds the {MAX_EVIDENCE_BYTES}-byte safety limit"
        )

    descriptor = _open_evidence_descriptor(path)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError("evidence file must be a regular file")
        _validate_file_trust(opened)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("evidence file changed before it could be read")
        filesystem_opened = _filesystem_identity(descriptor)
        body = _read_bounded_descriptor(descriptor)
        first_after = os.fstat(descriptor)
        filesystem_first_after = _filesystem_identity(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        verification_body = _read_bounded_descriptor(descriptor)
        second_after = os.fstat(descriptor)
        filesystem_second_after = _filesystem_identity(descriptor)
    except OSError as exc:
        raise ValueError(f"unable to read evidence file: {exc}") from exc
    finally:
        os.close(descriptor)

    _validate_file_trust(first_after)
    _validate_file_trust(second_after)
    if not (
        filesystem_opened == filesystem_first_after == filesystem_second_after
    ):
        raise ValueError("evidence filesystem changed during reading")
    if len(body) > MAX_EVIDENCE_BYTES:
        raise ValueError(
            f"evidence file exceeds the {MAX_EVIDENCE_BYTES}-byte safety limit"
        )
    if (
        len(body) != opened.st_size
        or _file_identity(opened) != _file_identity(first_after)
        or _file_identity(first_after) != _file_identity(second_after)
        or verification_body != body
    ):
        raise ValueError("evidence file changed during reading")

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("evidence file is not valid UTF-8") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
            parse_int=_parse_bounded_integer,
            parse_float=_reject_float,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("evidence file contains malformed JSON") from exc
    except RecursionError as exc:
        raise ValueError("evidence JSON nesting exceeds parser safety limits") from exc
    _validate_json_tree(payload)
    return payload


def _validate_missing_gate(gate: dict, index: int) -> None:
    if gate["status"] != "missing":
        raise ValueError(f"gate {index} missing evidence status is invalid")
    for field in (
        "conclusion", "run_id", "html_url", "event", "head_branch", "head_sha"
    ):
        if gate[field] is not None:
            raise ValueError(f"gate {index} missing evidence has invalid {field}")


def _validate_real_gate(
    gate: dict, index: int, repository: str, release_sha: str
) -> bool:
    status = _required_string(gate["status"], f"gate {index} status")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"gate {index} status is invalid")
    conclusion = _optional_string(gate["conclusion"], f"gate {index} conclusion")
    if status == "completed":
        if conclusion not in ALLOWED_CONCLUSIONS:
            raise ValueError(f"gate {index} conclusion is invalid")
    elif conclusion is not None:
        raise ValueError(f"gate {index} conclusion must be null before completion")

    event = _required_string(gate["event"], f"gate {index} event")
    branch = _required_string(gate["head_branch"], f"gate {index} head_branch")
    head_sha = _required_string(gate["head_sha"], f"gate {index} head_sha")
    if event != REQUIRED_EVENT:
        raise ValueError(f"gate {index} event is invalid")
    if branch != REQUIRED_BRANCH:
        raise ValueError(f"gate {index} head_branch is invalid")
    if not SHA_RE.fullmatch(head_sha) or head_sha != release_sha:
        raise ValueError(f"gate {index} head_sha is invalid")

    run_id = gate["run_id"]
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise ValueError(f"gate {index} run_id is invalid")
    html_url = _required_string(gate["html_url"], f"gate {index} html_url")
    expected_url = f"https://github.com/{repository}/actions/runs/{run_id}"
    if html_url != expected_url:
        raise ValueError(f"gate {index} html_url is invalid")
    return status == "completed" and conclusion == "success"


def validate_payload(payload: object, repository: str, release_sha: str) -> None:
    if not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("repository must use owner/name format")
    if not SHA_RE.fullmatch(release_sha):
        raise ValueError("release SHA must be 40 lowercase hexadecimal characters")
    if not isinstance(payload, dict):
        raise ValueError("evidence must be a JSON object")
    if set(payload) != TOP_LEVEL_KEYS:
        raise ValueError("evidence has missing or unexpected top-level fields")
    if payload["repository"] != repository:
        raise ValueError("evidence repository does not match the requested repository")
    if payload["release_sha"] != release_sha:
        raise ValueError("evidence release_sha does not match the requested SHA")
    if payload["required_event"] != REQUIRED_EVENT:
        raise ValueError("evidence required_event is invalid")
    if payload["required_branch"] != REQUIRED_BRANCH:
        raise ValueError("evidence required_branch is invalid")
    if payload["required_workflow_paths"] != REQUIRED_WORKFLOW_PATHS:
        raise ValueError("evidence required workflow map is invalid")
    if not isinstance(payload["passed"], bool):
        raise ValueError("evidence passed must be a boolean")

    gates = payload["gates"]
    if not isinstance(gates, list) or len(gates) != len(REQUIRED_WORKFLOW_PATHS):
        raise ValueError("evidence must contain exactly one gate per required workflow")

    recomputed_passed = True
    seen_run_ids: set[int] = set()
    seen_run_urls: set[str] = set()
    for index, (workflow_name, workflow_path) in enumerate(
        REQUIRED_WORKFLOW_PATHS.items()
    ):
        gate = gates[index]
        if not isinstance(gate, dict) or set(gate) != GATE_KEYS:
            raise ValueError(f"gate {index} has missing or unexpected fields")
        if gate["name"] != workflow_name or gate["path"] != workflow_path:
            raise ValueError(f"gate {index} identity or path is invalid")
        if gate["run_id"] is None:
            _validate_missing_gate(gate, index)
            gate_passed = False
        else:
            gate_passed = _validate_real_gate(gate, index, repository, release_sha)
            run_id = gate["run_id"]
            html_url = gate["html_url"]
            if run_id in seen_run_ids:
                raise ValueError(f"gate {index} reuses a prior run_id")
            if html_url in seen_run_urls:
                raise ValueError(f"gate {index} reuses a prior html_url")
            seen_run_ids.add(run_id)
            seen_run_urls.add(html_url)
        recomputed_passed = recomputed_passed and gate_passed

    if payload["passed"] != recomputed_passed:
        raise ValueError("evidence passed value is inconsistent with gate results")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--sha", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = _read_evidence(args.evidence)
        validate_payload(payload, args.repository, args.sha)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("VALID: release gate evidence artifact is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
