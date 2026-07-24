import hashlib
import json
from pathlib import Path

import pytest

from scripts.manage_internal_alpha_artifact_contract import (
    AUTHORIZED_REQUIRED,
    DECISION_PATH,
    DIAGNOSTIC_REQUIRED,
    SCOPE,
    build_contract,
    verify_contract,
    write_contract,
)


def decision_payload(*, authorized: bool) -> dict:
    failed_steps = [] if authorized else ["release-gates"]
    return {
        "authorization_scope": SCOPE,
        "authorized": authorized,
        "candidate": {
            "backend_digest": "sha256:" + "b" * 64,
            "candidate_sha": "c" * 40,
            "frontend_digest": "sha256:" + "f" * 64,
            "repository": "owner/repo",
        },
        "failed_steps": failed_steps,
        "provenance": {"run_attempt": 1, "run_id": 123, "workflow_sha": "a" * 40},
        "schema_version": 1,
        "steps": [],
    }


def write_decision(root: Path, *, authorized: bool) -> Path:
    path = root / DECISION_PATH
    path.write_text(json.dumps(decision_payload(authorized=authorized)), encoding="utf-8")
    return path


def create_files(root: Path, paths: tuple[str, ...]) -> list[Path]:
    result = []
    for name in sorted(paths):
        path = root / name
        if name != DECISION_PATH:
            path.write_text(f"evidence:{name}\n", encoding="utf-8")
        result.append(path)
    return result


def relative_files(root: Path, paths: tuple[str, ...]) -> list[Path]:
    return [path.relative_to(root) for path in create_files(root, paths)]


def run_from(root: Path, function, *args, **kwargs):
    previous = Path.cwd()
    try:
        import os

        os.chdir(root)
        return function(*args, **kwargs)
    finally:
        os.chdir(previous)


def test_authorized_contract_requires_and_binds_complete_canonical_set(tmp_path: Path):
    write_decision(tmp_path, authorized=True)
    files = relative_files(tmp_path, AUTHORIZED_REQUIRED)
    contract = Path("internal-alpha-authorization-artifact-contract.json")

    payload = run_from(
        tmp_path,
        build_contract,
        decision=Path(DECISION_PATH),
        contract=contract,
        files=files,
    )

    assert payload["authorized"] is True
    assert payload["required_paths"] == list(AUTHORIZED_REQUIRED)
    assert [item["path"] for item in payload["files"]] == sorted(AUTHORIZED_REQUIRED)
    decision_binding = next(item for item in payload["files"] if item["path"] == DECISION_PATH)
    expected = hashlib.sha256((tmp_path / DECISION_PATH).read_bytes()).hexdigest()
    assert decision_binding["sha256"] == expected


def test_diagnostic_contract_requires_minimum_decision_evidence(tmp_path: Path):
    write_decision(tmp_path, authorized=False)
    files = relative_files(tmp_path, DIAGNOSTIC_REQUIRED)

    payload = run_from(
        tmp_path,
        build_contract,
        decision=Path(DECISION_PATH),
        contract=Path("contract.json"),
        files=files,
    )

    assert payload["authorized"] is False
    assert payload["required_paths"] == list(DIAGNOSTIC_REQUIRED)
    assert [item["path"] for item in payload["files"]] == sorted(DIAGNOSTIC_REQUIRED)


def test_authorized_contract_rejects_missing_declared_path(tmp_path: Path):
    write_decision(tmp_path, authorized=True)
    declared = tuple(path for path in AUTHORIZED_REQUIRED if path != "internal-alpha-readiness-validation.txt")
    files = relative_files(tmp_path, declared)

    with pytest.raises(ValueError, match="required artifact paths were not declared"):
        run_from(
            tmp_path,
            build_contract,
            decision=Path(DECISION_PATH),
            contract=Path("contract.json"),
            files=files,
        )


def test_contract_rejects_declared_required_file_missing_on_disk(tmp_path: Path):
    write_decision(tmp_path, authorized=False)
    files = [Path(name) for name in sorted(DIAGNOSTIC_REQUIRED)]
    (tmp_path / DIAGNOSTIC_REQUIRED[1]).write_text("generation\n", encoding="utf-8")

    with pytest.raises(ValueError, match="required artifact files are missing"):
        run_from(
            tmp_path,
            build_contract,
            decision=Path(DECISION_PATH),
            contract=Path("contract.json"),
            files=files,
        )


def test_contract_rejects_unexpected_duplicate_unsorted_and_self_paths(tmp_path: Path):
    write_decision(tmp_path, authorized=False)
    relative_files(tmp_path, DIAGNOSTIC_REQUIRED)
    canonical = [Path(name) for name in sorted(DIAGNOSTIC_REQUIRED)]

    with pytest.raises(ValueError, match="unexpected artifact paths"):
        run_from(
            tmp_path,
            build_contract,
            decision=Path(DECISION_PATH),
            contract=Path("contract.json"),
            files=[*canonical, Path("unexpected.txt")],
        )
    with pytest.raises(ValueError, match="unique"):
        run_from(
            tmp_path,
            build_contract,
            decision=Path(DECISION_PATH),
            contract=Path("contract.json"),
            files=[*canonical, canonical[-1]],
        )
    with pytest.raises(ValueError, match="sorted"):
        run_from(
            tmp_path,
            build_contract,
            decision=Path(DECISION_PATH),
            contract=Path("contract.json"),
            files=list(reversed(canonical)),
        )
    with pytest.raises(ValueError, match="cannot bind itself"):
        run_from(
            tmp_path,
            build_contract,
            decision=Path(DECISION_PATH),
            contract=canonical[0],
            files=canonical,
        )


def test_contract_rejects_symlink_and_weakened_or_inconsistent_decision(tmp_path: Path):
    write_decision(tmp_path, authorized=False)
    relative_files(tmp_path, DIAGNOSTIC_REQUIRED)
    link = tmp_path / DIAGNOSTIC_REQUIRED[1]
    link.unlink()
    link.symlink_to(tmp_path / DECISION_PATH)
    files = [Path(name) for name in sorted(DIAGNOSTIC_REQUIRED)]

    with pytest.raises(ValueError, match="symlinked"):
        run_from(
            tmp_path,
            build_contract,
            decision=Path(DECISION_PATH),
            contract=Path("contract.json"),
            files=files,
        )

    payload = decision_payload(authorized=False)
    payload["authorization_scope"] = {**SCOPE, "public_access_authorized": True}
    (tmp_path / DECISION_PATH).write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="weakens"):
        run_from(
            tmp_path,
            build_contract,
            decision=Path(DECISION_PATH),
            contract=Path("contract.json"),
            files=files,
        )

    payload = decision_payload(authorized=True)
    payload["failed_steps"] = ["release-gates"]
    (tmp_path / DECISION_PATH).write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="conflicts"):
        run_from(
            tmp_path,
            build_contract,
            decision=Path(DECISION_PATH),
            contract=Path("contract.json"),
            files=files,
        )


def test_verifier_detects_contract_and_bound_file_mutation(tmp_path: Path):
    write_decision(tmp_path, authorized=False)
    files = relative_files(tmp_path, DIAGNOSTIC_REQUIRED)
    contract = Path("internal-alpha-authorization-artifact-contract.json")
    payload = run_from(
        tmp_path,
        build_contract,
        decision=Path(DECISION_PATH),
        contract=contract,
        files=files,
    )
    run_from(tmp_path, write_contract, contract, payload)
    run_from(tmp_path, verify_contract, contract, payload)

    (tmp_path / DIAGNOSTIC_REQUIRED[1]).write_text("mutated\n", encoding="utf-8")
    changed = run_from(
        tmp_path,
        build_contract,
        decision=Path(DECISION_PATH),
        contract=contract,
        files=files,
    )
    with pytest.raises(ValueError, match="does not match"):
        run_from(tmp_path, verify_contract, contract, changed)

    (tmp_path / contract).write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        run_from(tmp_path, verify_contract, contract, changed)
