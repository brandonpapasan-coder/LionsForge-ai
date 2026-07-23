import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "validate_public_operations_activation.py"
)
SPEC = spec_from_file_location("validate_public_operations_activation", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
validate_record = MODULE.validate_record


def valid_record(*, decision: str = "GO", defects: str = "0") -> str:
    policies = [
        "Privacy Notice",
        "Terms of Service",
        "Responsible AI disclosure",
        "Data retention and deletion policy",
        "Acceptable use and abuse reporting",
    ]
    channels = [
        "General support",
        "Privacy requests",
        "Security reports",
        "Abuse reports",
    ]
    retention = [
        "Account records",
        "Investigation and workspace data",
        "Education and mastery history",
        "Authentication and security logs",
        "Application and provider logs",
        "Backups",
        "Support and privacy-request records",
    ]
    workflows = [
        "Privacy request intake",
        "Identity verification",
        "Account closure and authentication disablement",
        "Eligible data deletion or de-identification",
        "Backup-expiry handling",
        "General support intake and response",
        "Abuse report intake and escalation",
        "Security report intake and escalation",
        "Consent recording and policy-version capture",
    ]
    approvals = [
        "Business owner",
        "Legal reviewer",
        "Privacy owner",
        "Security owner",
        "Support operations owner",
        "Release owner",
    ]

    lines = [
        "# Public Operations Activation Record",
        "- Release candidate SHA: " + "a" * 40,
        "- Record owner role: Release Owner",
        "- Review date: 2026-07-20",
        "- Intended effective date: 2026-08-01",
        f"- Decision: **{decision}**",
        "- Public legal entity name: LionsForge AI LLC",
        "- Public business address or approved registered-agent address: controlled-private-record",
        "- Governing-law and venue language approved: Yes",
        "- Supported launch jurisdictions: United States",
        "- Age eligibility and parental-consent position: Adults only",
        "- Jurisdiction-specific privacy-rights matrix reference: controlled-record-1",
        "- Subprocessor and AI-provider disclosure reference: controlled-record-2",
        "- Support response target: 2 business days",
        "- Privacy-request response target: 30 days",
        "- Security-report acknowledgment target: 1 business day",
        "- Abuse-report acknowledgment target: 1 business day",
        "- After-hours critical incident coverage: On-call owner",
        "- Escalation owner role: Operations Owner",
        "| Surface | Version or SHA | Effective date | Business approver role | "
        "Legal approver role | Status |",
        "|---|---|---|---|---|---|",
    ]
    lines.extend(
        f"| {name} | v1 | 2026-08-01 | Business Owner | Legal Reviewer | APPROVED |"
        for name in policies
    )
    lines.extend(
        [
            "| Function | Public channel | Operational owner role | "
            "Monitoring verified | Test evidence reference |",
            "|---|---|---|---|---|",
        ]
    )
    lines.extend(
        f"| {name} | public@example.test | Operations Owner | VERIFIED | evidence |"
        for name in channels
    )
    lines.extend(
        [
            "| Data class | Approved retention period | Deletion or "
            "de-identification behavior | Backup exception | Approval status |",
            "|---|---|---|---|---|",
        ]
    )
    lines.extend(
        f"| {name} | 30 days | Delete | Expires with backup | APPROVED |" for name in retention
    )
    lines.extend(
        [
            "| Workflow | Test date | Tester role | Evidence reference | Result |",
            "|---|---|---|---|---|",
        ]
    )
    lines.extend(f"| {name} | 2026-07-20 | Tester | evidence | PASSED |" for name in workflows)
    lines.extend(
        [
            "- Log-redaction review completed: YES",
            "- Secrets and credentials excluded from logs: VERIFIED",
            "- Private prompts, evidence, education records, and support content "
            "excluded or minimized: VERIFIED",
            "- Analytics and cookie inventory completed: YES",
            "- Consent control required: YES",
            "- Consent control tested when required: PASSED",
            f"- Open high or critical privacy/security defects: {defects}",
            "| Approval | Approver role | Date | Status |",
            "|---|---|---|---|",
        ]
    )
    lines.extend(f"| {name} | {name} | 2026-07-20 | APPROVED |" for name in approvals)
    return "\n".join(lines)


def codes(text: str) -> set[str]:
    return {finding.code for finding in validate_record(text)}


def test_valid_go_record_passes() -> None:
    assert validate_record(valid_record()) == []


def test_complete_no_go_record_fails_activation() -> None:
    assert "decision-no-go" in codes(valid_record(decision="NO-GO"))


def test_invalid_release_sha_fails() -> None:
    text = valid_record().replace("a" * 40, "main", 1)
    assert "invalid-sha" in codes(text)


def test_missing_public_address_fails() -> None:
    text = valid_record().replace(
        "- Public business address or approved registered-agent address: controlled-private-record",
        "- Public business address or approved registered-agent address: PENDING",
    )
    assert "missing-field" in codes(text)


def test_negative_legal_approval_fails() -> None:
    text = valid_record().replace(
        "- Governing-law and venue language approved: Yes",
        "- Governing-law and venue language approved: No",
    )
    assert "legal-approval-incomplete" in codes(text)


def test_invalid_review_date_fails() -> None:
    text = valid_record().replace(
        "- Review date: 2026-07-20",
        "- Review date: July 20, 2026",
    )
    assert "invalid-date" in codes(text)


def test_effective_date_before_review_fails() -> None:
    text = valid_record().replace(
        "- Intended effective date: 2026-08-01",
        "- Intended effective date: 2026-07-01",
        1,
    )
    assert "invalid-date-order" in codes(text)


def test_placeholder_controlled_reference_fails() -> None:
    text = valid_record().replace(
        "- Jurisdiction-specific privacy-rights matrix reference: controlled-record-1",
        "- Jurisdiction-specific privacy-rights matrix reference: TODO",
    )
    assert "invalid-reference" in codes(text)


def test_unapproved_policy_and_unverified_channel_fail() -> None:
    text = valid_record().replace(
        "| Privacy Notice | v1 | 2026-08-01 | Business Owner | Legal Reviewer | APPROVED |",
        "| Privacy Notice | PENDING | PENDING | PENDING | PENDING | NOT APPROVED |",
    )
    text = text.replace(
        "| General support | public@example.test | Operations Owner | VERIFIED | evidence |",
        "| General support | PENDING | PENDING | NOT VERIFIED | PENDING |",
    )
    assert {
        "policy-unapproved",
        "policy-incomplete",
        "channel-unverified",
        "channel-incomplete",
    }.issubset(codes(text))


def test_untested_deletion_workflow_fails() -> None:
    text = valid_record().replace(
        "| Eligible data deletion or de-identification | 2026-07-20 | Tester | evidence | PASSED |",
        "| Eligible data deletion or de-identification | PENDING | PENDING | "
        "PENDING | NOT TESTED |",
    )
    assert {"workflow-untested", "workflow-incomplete"}.issubset(codes(text))


def test_incomplete_privacy_controls_fail() -> None:
    text = valid_record().replace(
        "- Log-redaction review completed: YES",
        "- Log-redaction review completed: NO",
    )
    assert "privacy-control-incomplete" in codes(text)


def test_required_consent_control_must_be_tested() -> None:
    text = valid_record().replace(
        "- Consent control tested when required: PASSED",
        "- Consent control tested when required: NOT TESTED",
    )
    assert "consent-control-untested" in codes(text)


def test_go_rejects_blocking_defects() -> None:
    findings = validate_record(valid_record(defects="1"))
    assert {"blocking-defect", "invalid-go"}.issubset({finding.code for finding in findings})


def test_missing_final_approval_fails() -> None:
    text = valid_record().replace(
        "| Legal reviewer | Legal reviewer | 2026-07-20 | APPROVED |",
        "| Legal reviewer | PENDING | PENDING | NOT APPROVED |",
    )
    assert {"approval-missing", "approval-incomplete"}.issubset(codes(text))
