import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_internal_alpha_evidence.py"
SPEC = spec_from_file_location("validate_internal_alpha_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
validate_evidence = MODULE.validate_evidence


def record(*, decision: str = "GO", evidence: str = "Run 1744") -> str:
    return "\n".join(
        [
            "# Internal Alpha Readiness Gate",
            f"- Decision: **{decision}**",
            "",
            "| Control | Status | Evidence |",
            "|---|---|---|",
            f"| Required CI checks passed | VERIFIED | {evidence} |",
            "",
            "| Approval | Status |",
            "|---|---|",
            "| Release owner | APPROVED |",
        ]
    )


def codes(text: str) -> set[str]:
    return {finding.code for finding in validate_evidence(text)}


def test_no_go_allows_pending_evidence():
    assert validate_evidence(record(decision="NO-GO", evidence="PENDING")) == []


def test_go_accepts_numbered_references():
    for evidence in ("PR #484", "Issue 485", "Run 1744", "Artifact 9123"):
        assert validate_evidence(record(evidence=evidence)) == []


def test_go_accepts_urls_paths_shas_and_digests():
    accepted = (
        "https://github.com/example/repo/actions/runs/1744",
        "docs/operations/staging-acceptance.md",
        "a" * 40,
        "sha256:" + "b" * 64,
    )
    for evidence in accepted:
        assert validate_evidence(record(evidence=evidence)) == []


def test_go_rejects_generic_evidence_text():
    for evidence in ("complete", "completed", "done", "evidence", "passed", "verified"):
        assert "missing-evidence-reference" in codes(record(evidence=evidence))


def test_go_rejects_untraceable_free_text():
    assert "missing-evidence-reference" in codes(
        record(evidence="validated by the team during staging")
    )


def test_final_approval_table_does_not_require_evidence_column():
    assert validate_evidence(record()) == []


def test_rejects_malformed_evidence_row():
    text = record().replace(
        "| Required CI checks passed | VERIFIED | Run 1744 |",
        "| Required CI checks passed | VERIFIED |",
    )
    assert "malformed-evidence-row" in codes(text)


def test_requires_a_valid_decision():
    assert "invalid-decision" in codes(record().replace("**GO**", "**READY**"))
