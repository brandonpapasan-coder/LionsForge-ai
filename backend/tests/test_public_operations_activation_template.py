import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs" / "public-operations-activation-record.md"


Validator = Callable[[str], list[object]]


def _load_validator(module_name: str, script_name: str) -> Validator:
    script = ROOT / "scripts" / script_name
    spec = spec_from_file_location(module_name, script)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.validate_record


validate_activation = _load_validator(
    "validate_public_operations_activation_template_contract",
    "validate_public_operations_activation.py",
)
validate_row_evidence = _load_validator(
    "validate_public_operations_row_evidence_template_contract",
    "validate_public_operations_row_evidence.py",
)


REQUIRED_ROWS = {
    "Privacy Notice",
    "Terms of Service",
    "Responsible AI disclosure",
    "Data retention and deletion policy",
    "Acceptable use and abuse reporting",
    "General support",
    "Privacy requests",
    "Security reports",
    "Abuse reports",
    "Account records",
    "Investigation and workspace data",
    "Education and mastery history",
    "Authentication and security logs",
    "Application and provider logs",
    "Backups",
    "Support and privacy-request records",
    "Privacy request intake",
    "Identity verification",
    "Account closure and authentication disablement",
    "Eligible data deletion or de-identification",
    "Backup-expiry handling",
    "General support intake and response",
    "Abuse report intake and escalation",
    "Security report intake and escalation",
    "Consent recording and policy-version capture",
    "Business owner",
    "Legal reviewer",
    "Privacy owner",
    "Security owner",
    "Support operations owner",
    "Release owner",
}


def _codes(findings: list[object]) -> set[str]:
    return {str(getattr(finding, "code")) for finding in findings}


def test_template_remains_fail_closed() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "- Decision: **NO-GO**" in text
    assert "Public registration remains disabled" in text
    assert "private home-address" in text
    assert "deployed public build" not in text

    activation_codes = _codes(validate_activation(text))
    assert {
        "invalid-sha",
        "decision-no-go",
        "invalid-date",
        "legal-approval-incomplete",
        "invalid-reference",
        "policy-unapproved",
        "channel-unverified",
        "retention-unapproved",
        "workflow-untested",
        "approval-missing",
        "privacy-control-incomplete",
        "consent-decision-incomplete",
        "blocking-defect",
    }.issubset(activation_codes)

    row_codes = _codes(validate_row_evidence(text))
    assert {
        "invalid-row-date",
        "invalid-row-reference",
    }.issubset(row_codes)


def test_template_contains_all_required_rows() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    for row in REQUIRED_ROWS:
        assert f"| {row} |" in text


def test_template_documents_date_and_evidence_rules() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "YYYY-MM-DD" in text
    assert "non-placeholder evidence reference" in text
    assert "exact-SHA release gates" in text
    assert "both public-operations validators succeed" in text
