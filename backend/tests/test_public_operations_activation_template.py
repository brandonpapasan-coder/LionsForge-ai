import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs" / "public-operations-activation-record.md"


def _load_validator(module_name: str, script_name: str):
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


def test_template_remains_fail_closed() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")

    assert "- Decision: **NO-GO**" in text
    assert "Public registration remains disabled" in text
    assert "private home-address" in text
    assert "deployed public build" not in text
    assert validate_activation(text)
    assert validate_row_evidence(text)


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
