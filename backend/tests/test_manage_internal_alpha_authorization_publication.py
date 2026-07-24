import hashlib
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "manage_internal_alpha_authorization_publication.py"
SPEC = spec_from_file_location("manage_internal_alpha_authorization_publication", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

SCOPE = MODULE.SCOPE
build_publication = MODULE.build_publication
verify_publication = MODULE.verify_publication
write_publication = MODULE.write_publication


def decision_payload(*, authorized: bool = True) -> dict:
    return {
        "authorization_scope": SCOPE,
        "authorized": authorized,
        "candidate": {
            "backend_digest": "sha256:" + "b" * 64,
            "candidate_sha": "c" * 40,
            "frontend_digest": "sha256:" + "f" * 64,
            "repository": "owner/repo",
        },
        "failed_steps": [] if authorized else ["release-gates"],
        "provenance": {
            "run_attempt": 1,
            "run_id": 123,
            "workflow_sha": "a" * 40,
        },
        "schema_version": 1,
        "steps": [],
    }


def contract_payload(*, authorized: bool = True) -> dict:
    return {
        "authorization_scope": SCOPE,
        "authorized": authorized,
        "files": [],
        "required_paths": [],
        "schema_version": 1,
    }


def write_sources(root: Path, *, authorized: bool = True) -> tuple[Path, Path]:
    decision = root / "internal-alpha-authorization-decision.json"
    contract = root / "internal-alpha-authorization-artifact-contract.json"
    decision.write_text(
        json.dumps(decision_payload(authorized=authorized)), encoding="utf-8"
    )
    contract.write_text(
        json.dumps(contract_payload(authorized=authorized)), encoding="utf-8"
    )
    return decision, contract


def test_publication_binds_verified_sources_deterministically(tmp_path: Path):
    decision, contract = write_sources(tmp_path)
    payload = build_publication(
        decision=decision,
        contract=contract,
        artifact_name="internal-alpha-authorization-evidence",
    )
    assert payload["authorized"] is True
    assert payload["authorization_scope"] == SCOPE
    assert payload["artifact"]["contract_sha256"] == hashlib.sha256(
        contract.read_bytes()
    ).hexdigest()
    output = tmp_path / "publication.json"
    write_publication(output, payload)
    first = output.read_bytes()
    write_publication(output, payload)
    assert output.read_bytes() == first
    verify_publication(output, payload)


def test_publication_preserves_fail_closed_non_authorized_state(tmp_path: Path):
    decision, contract = write_sources(tmp_path, authorized=False)
    payload = build_publication(
        decision=decision,
        contract=contract,
        artifact_name="internal-alpha-authorization-evidence",
    )
    assert payload["authorized"] is False


def test_publication_rejects_inconsistent_or_weakened_sources(tmp_path: Path):
    decision, contract = write_sources(tmp_path)
    contract.write_text(
        json.dumps(contract_payload(authorized=False)), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="inconsistent"):
        build_publication(decision=decision, contract=contract, artifact_name="evidence")

    contract_value = contract_payload()
    contract_value["authorization_scope"] = {
        **SCOPE,
        "public_access_authorized": True,
    }
    contract.write_text(json.dumps(contract_value), encoding="utf-8")
    with pytest.raises(ValueError, match="weaken"):
        build_publication(decision=decision, contract=contract, artifact_name="evidence")


def test_publication_rejects_invalid_provenance_and_artifact_name(tmp_path: Path):
    decision, contract = write_sources(tmp_path)
    value = decision_payload()
    value["provenance"]["run_id"] = True
    decision.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="positive integer"):
        build_publication(decision=decision, contract=contract, artifact_name="evidence")

    decision.write_text(json.dumps(decision_payload()), encoding="utf-8")
    with pytest.raises(ValueError, match="artifact name"):
        build_publication(decision=decision, contract=contract, artifact_name="bad/name")


def test_publication_rejects_symlink_and_distinct_source_violation(tmp_path: Path):
    decision, contract = write_sources(tmp_path)
    link = tmp_path / "contract-link.json"
    link.symlink_to(contract)
    with pytest.raises(ValueError, match="symlinked"):
        build_publication(decision=decision, contract=link, artifact_name="evidence")
    with pytest.raises(ValueError, match="distinct"):
        build_publication(decision=decision, contract=decision, artifact_name="evidence")


def test_verifier_detects_source_and_record_mutation(tmp_path: Path):
    decision, contract = write_sources(tmp_path)
    output = tmp_path / "publication.json"
    payload = build_publication(
        decision=decision,
        contract=contract,
        artifact_name="evidence",
    )
    write_publication(output, payload)

    contract.write_text(
        json.dumps({**contract_payload(), "files": [{"path": "changed"}]}),
        encoding="utf-8",
    )
    changed = build_publication(
        decision=decision,
        contract=contract,
        artifact_name="evidence",
    )
    with pytest.raises(ValueError, match="does not match"):
        verify_publication(output, changed)

    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        verify_publication(output, changed)
