from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_launch_evidence_chain.py"
spec = importlib.util.spec_from_file_location("validate_launch_evidence_chain", SCRIPT)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)

SHA = "a" * 40
ROLLBACK = "b" * 40
BACKEND = "sha256:" + "c" * 64
FRONTEND = "sha256:" + "d" * 64


def records(beta_sha: str = SHA, ga_decision: str = "GO") -> dict[str, str]:
    return {
        "production": f"""- Release SHA: {SHA}\n- Rollback SHA: {ROLLBACK}\n- Backend image digest: {BACKEND}\n- Frontend image digest: {FRONTEND}\n- Decision: GO\n""",
        "public_operations": f"""- Release candidate SHA: {SHA}\n- Decision: GO\n""",
        "controlled_beta": f"""- Release SHA: {beta_sha}\n- Previous rollback SHA: {ROLLBACK}\n- Backend image digest: {BACKEND}\n- Frontend image digest: {FRONTEND}\n- [x] GO — complete\n""",
        "ga": f"""- Release SHA: {SHA}\n- Previous rollback SHA: {ROLLBACK}\n- Backend image digest: {BACKEND}\n- Frontend image digest: {FRONTEND}\n- Production acceptance evidence: production-001\n- Public-operations activation evidence: public-ops-001\n- Controlled-beta acceptance evidence: beta-001\n- Candidate ancestry evidence: ancestry-001\n- [x] {ga_decision} — decision\n""",
    }


def allow_standalone(monkeypatch):
    monkeypatch.setattr(
        validator,
        "_load_module",
        lambda *_args, **_kwargs: SimpleNamespace(validate_record=lambda _text: []),
    )


def test_consistent_chain_is_valid(monkeypatch):
    allow_standalone(monkeypatch)
    assert validator.validate_chain(records()) == []


def test_propagates_standalone_validator_findings(monkeypatch):
    finding = SimpleNamespace(code="invalid-sha", message="bad release")
    monkeypatch.setattr(
        validator,
        "_load_module",
        lambda name, _path: SimpleNamespace(
            validate_record=lambda _text: [finding] if name == "production" else []
        ),
    )
    results = validator.validate_chain(records())
    assert any(f.code == "record-invalid" and f.record == "production" for f in results)


def test_rejects_release_digest_and_rollback_mismatches(monkeypatch):
    allow_standalone(monkeypatch)
    chain = records()
    chain["production"] = chain["production"].replace(SHA, "e" * 40).replace(
        BACKEND, "sha256:" + "f" * 64
    ).replace(ROLLBACK, "9" * 40)
    results = validator.validate_chain(chain)
    messages = [f.message for f in results if f.code == "identity-mismatch"]
    assert any("release SHA" in message for message in messages)
    assert any("rollback SHA" in message for message in messages)
    assert any("backend image digest" in message for message in messages)


def test_rejects_public_operations_candidate_mismatch(monkeypatch):
    allow_standalone(monkeypatch)
    chain = records()
    chain["public_operations"] = chain["public_operations"].replace(SHA, "e" * 40)
    assert any(
        f.code == "identity-mismatch" and "public-operations" in f.message
        for f in validator.validate_chain(chain)
    )


def test_allows_documented_beta_predecessor(monkeypatch):
    allow_standalone(monkeypatch)
    chain = records(beta_sha="e" * 40)
    assert not any(f.code in {"missing-ancestry", "ambiguous-lineage"} for f in validator.validate_chain(chain))


def test_rejects_undocumented_or_ambiguous_beta_lineage(monkeypatch):
    allow_standalone(monkeypatch)
    undocumented = records(beta_sha="e" * 40)
    undocumented["ga"] = undocumented["ga"].replace("- Candidate ancestry evidence: ancestry-001", "- Candidate ancestry evidence:")
    assert any(f.code == "missing-ancestry" for f in validator.validate_chain(undocumented))

    ambiguous = records()
    ambiguous["controlled_beta"] = ambiguous["controlled_beta"].replace(BACKEND, "sha256:" + "f" * 64)
    assert any(f.code == "ambiguous-lineage" for f in validator.validate_chain(ambiguous))


def test_rejects_missing_and_duplicate_evidence_bindings(monkeypatch):
    allow_standalone(monkeypatch)
    chain = records()
    chain["ga"] = chain["ga"].replace("- Production acceptance evidence: production-001", "- Production acceptance evidence:")
    assert any(f.code == "missing-binding" for f in validator.validate_chain(chain))

    duplicate = records()
    duplicate["ga"] = duplicate["ga"].replace("public-ops-001", "production-001")
    assert any(f.code == "duplicate-binding" for f in validator.validate_chain(duplicate))


def test_ga_go_requires_all_upstream_go(monkeypatch):
    allow_standalone(monkeypatch)
    chain = records()
    chain["production"] = chain["production"].replace("- Decision: GO", "- Decision: NO-GO")
    chain["controlled_beta"] = chain["controlled_beta"].replace("[x] GO", "[x] NO-GO")
    results = validator.validate_chain(chain)
    assert sum(f.code == "decision-order" for f in results) == 2


def test_findings_are_deterministic(monkeypatch):
    allow_standalone(monkeypatch)
    chain = records()
    chain["public_operations"] = chain["public_operations"].replace(SHA, "e" * 40)
    chain["ga"] = chain["ga"].replace("public-ops-001", "production-001")
    first = validator.validate_chain(chain)
    second = validator.validate_chain(chain)
    assert first == second
    assert first == sorted(first)


def test_cli_reports_unreadable_record(tmp_path: Path):
    paths = [tmp_path / name for name in ("production.md", "public.md", "beta.md")]
    for path in paths:
        path.write_text("record", encoding="utf-8")
    missing = tmp_path / "missing-ga.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *(str(path) for path in paths), str(missing)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "record-unreadable [ga]" in result.stderr
