#!/usr/bin/env python3
"""Validate a completed LionsForge AI public operations activation record."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FIELD_RE = re.compile(r"^- ([^:]+):\s*(.*)$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
PLACEHOLDERS = {
    "",
    "PENDING",
    "NOT VERIFIED",
    "NOT TESTED",
    "NOT APPROVED",
    "TBD",
    "TODO",
    "N/A OR PENDING",
    "NOT APPLICABLE OR PENDING",
}

REQUIRED_POLICY_SURFACES = {
    "Privacy Notice",
    "Terms of Service",
    "Responsible AI disclosure",
    "Data retention and deletion policy",
    "Acceptable use and abuse reporting",
}
REQUIRED_CHANNELS = {
    "General support",
    "Privacy requests",
    "Security reports",
    "Abuse reports",
}
REQUIRED_RETENTION_CLASSES = {
    "Account records",
    "Investigation and workspace data",
    "Education and mastery history",
    "Authentication and security logs",
    "Application and provider logs",
    "Backups",
    "Support and privacy-request records",
}
REQUIRED_WORKFLOWS = {
    "Privacy request intake",
    "Identity verification",
    "Account closure and authentication disablement",
    "Eligible data deletion or de-identification",
    "Backup-expiry handling",
    "General support intake and response",
    "Abuse report intake and escalation",
    "Security report intake and escalation",
    "Consent recording and policy-version capture",
}
REQUIRED_APPROVALS = {
    "Business owner",
    "Legal reviewer",
    "Privacy owner",
    "Security owner",
    "Support operations owner",
    "Release owner",
}


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


def _normalize(value: str) -> str:
    return value.strip().strip("`").strip("*").strip()


def _upper(value: str) -> str:
    return _normalize(value).upper()


def _is_placeholder(value: str) -> bool:
    return _upper(value) in PLACEHOLDERS


def _fields(lines: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in lines:
        match = FIELD_RE.match(line.strip())
        if match:
            result[match.group(1).strip()] = _normalize(match.group(2))
    return result


def _rows(lines: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for line in lines:
        match = TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        cells = [_normalize(cell) for cell in match.group(1).split("|")]
        if not cells or cells[0] in {
            "Surface",
            "Function",
            "Data class",
            "Workflow",
            "Approval",
            "---",
        }:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells if cell):
            continue
        result[cells[0]] = cells[1:]
    return result


def _require_rows(
    rows: dict[str, list[str]],
    names: set[str],
    findings: list[Finding],
    group: str,
) -> None:
    for name in sorted(names):
        if name not in rows:
            findings.append(Finding("missing-row", f"{group} row is missing: {name}"))


def _require_iso_date(
    fields: dict[str, str], field: str, findings: list[Finding]
) -> date | None:
    value = fields.get(field, "")
    try:
        return date.fromisoformat(value)
    except ValueError:
        findings.append(
            Finding("invalid-date", f"{field} must use a valid YYYY-MM-DD date")
        )
        return None


def _require_reference(
    fields: dict[str, str], field: str, findings: list[Finding]
) -> None:
    value = fields.get(field, "")
    if _is_placeholder(value) or len(value.strip()) < 3:
        findings.append(
            Finding("invalid-reference", f"Evidence reference is incomplete: {field}")
        )


def validate_record(text: str) -> list[Finding]:
    lines = text.splitlines()
    fields = _fields(lines)
    rows = _rows(lines)
    findings: list[Finding] = []

    sha = fields.get("Release candidate SHA", "")
    if not SHA_RE.fullmatch(sha):
        findings.append(
            Finding(
                "invalid-sha",
                "Release candidate SHA must be exactly 40 lowercase hexadecimal characters",
            )
        )

    decision = _upper(fields.get("Decision", ""))
    if decision not in {"GO", "NO-GO"}:
        findings.append(Finding("invalid-decision", "Decision must be GO or NO-GO"))
    elif decision != "GO":
        findings.append(
            Finding(
                "decision-no-go",
                "Activation validation requires the final recorded decision to be GO",
            )
        )

    ordinary_fields = (
        "Record owner role",
        "Public legal entity name",
        "Public business address or approved registered-agent address",
        "Supported launch jurisdictions",
        "Age eligibility and parental-consent position",
        "Support response target",
        "Privacy-request response target",
        "Security-report acknowledgment target",
        "Abuse-report acknowledgment target",
        "After-hours critical incident coverage",
        "Escalation owner role",
    )
    for field in ordinary_fields:
        if _is_placeholder(fields.get(field, "")):
            findings.append(
                Finding("missing-field", f"Required field is incomplete: {field}")
            )

    review_date = _require_iso_date(fields, "Review date", findings)
    effective_date = _require_iso_date(fields, "Intended effective date", findings)
    if review_date and effective_date and effective_date < review_date:
        findings.append(
            Finding(
                "invalid-date-order",
                "Intended effective date cannot be earlier than the review date",
            )
        )

    if _upper(fields.get("Governing-law and venue language approved", "")) not in {
        "YES",
        "APPROVED",
        "VERIFIED",
    }:
        findings.append(
            Finding(
                "legal-approval-incomplete",
                "Governing-law and venue language must be affirmatively approved",
            )
        )

    for field in (
        "Jurisdiction-specific privacy-rights matrix reference",
        "Subprocessor and AI-provider disclosure reference",
    ):
        _require_reference(fields, field, findings)

    _require_rows(rows, REQUIRED_POLICY_SURFACES, findings, "Policy")
    _require_rows(rows, REQUIRED_CHANNELS, findings, "Monitored channel")
    _require_rows(rows, REQUIRED_RETENTION_CLASSES, findings, "Retention")
    _require_rows(rows, REQUIRED_WORKFLOWS, findings, "Workflow")
    _require_rows(rows, REQUIRED_APPROVALS, findings, "Approval")

    for name in REQUIRED_POLICY_SURFACES:
        cells = rows.get(name, [])
        if len(cells) < 5 or _upper(cells[4]) != "APPROVED":
            findings.append(Finding("policy-unapproved", f"Policy must be APPROVED: {name}"))
        if len(cells) < 4 or any(_is_placeholder(value) for value in cells[:4]):
            findings.append(Finding("policy-incomplete", f"Policy metadata is incomplete: {name}"))

    for name in REQUIRED_CHANNELS:
        cells = rows.get(name, [])
        if len(cells) < 4 or _upper(cells[2]) != "VERIFIED":
            findings.append(
                Finding("channel-unverified", f"Channel monitoring must be VERIFIED: {name}")
            )
        if len(cells) < 4 or any(_is_placeholder(value) for value in cells[:4]):
            findings.append(Finding("channel-incomplete", f"Channel metadata is incomplete: {name}"))

    for name in REQUIRED_RETENTION_CLASSES:
        cells = rows.get(name, [])
        if len(cells) < 4 or _upper(cells[3]) != "APPROVED":
            findings.append(
                Finding("retention-unapproved", f"Retention configuration must be APPROVED: {name}")
            )
        if len(cells) < 4 or any(_is_placeholder(value) for value in cells[:4]):
            findings.append(Finding("retention-incomplete", f"Retention metadata is incomplete: {name}"))

    for name in REQUIRED_WORKFLOWS:
        cells = rows.get(name, [])
        if len(cells) < 4 or _upper(cells[3]) != "PASSED":
            findings.append(Finding("workflow-untested", f"Workflow must be PASSED: {name}"))
        if len(cells) < 4 or any(_is_placeholder(value) for value in cells[:4]):
            findings.append(Finding("workflow-incomplete", f"Workflow evidence is incomplete: {name}"))

    for name in REQUIRED_APPROVALS:
        cells = rows.get(name, [])
        if len(cells) < 3 or _upper(cells[2]) != "APPROVED":
            findings.append(Finding("approval-missing", f"Final approval must be APPROVED: {name}"))
        if len(cells) < 3 or any(_is_placeholder(value) for value in cells[:3]):
            findings.append(Finding("approval-incomplete", f"Approval metadata is incomplete: {name}"))

    for field in (
        "Log-redaction review completed",
        "Secrets and credentials excluded from logs",
        "Private prompts, evidence, education records, and support content excluded or minimized",
        "Analytics and cookie inventory completed",
    ):
        if _upper(fields.get(field, "")) not in {"YES", "VERIFIED"}:
            findings.append(Finding("privacy-control-incomplete", f"Privacy control is incomplete: {field}"))

    consent_required = _upper(fields.get("Consent control required", ""))
    consent_tested = _upper(fields.get("Consent control tested when required", ""))
    if consent_required not in {"YES", "NO", "NOT REQUIRED"}:
        findings.append(
            Finding(
                "consent-decision-incomplete",
                "Consent control requirement must be explicitly YES, NO, or NOT REQUIRED",
            )
        )
    elif consent_required == "YES" and consent_tested not in {"YES", "VERIFIED", "PASSED"}:
        findings.append(
            Finding("consent-control-untested", "Required consent controls must be tested successfully")
        )
    elif consent_required in {"NO", "NOT REQUIRED"} and consent_tested not in {
        "NOT APPLICABLE",
        "YES",
        "VERIFIED",
        "PASSED",
    }:
        findings.append(
            Finding(
                "consent-control-incomplete",
                "Consent testing status must be explicit even when consent is not required",
            )
        )

    if _upper(fields.get("Open high or critical privacy/security defects", "")) not in {
        "0",
        "NONE",
    }:
        findings.append(
            Finding(
                "blocking-defect",
                "GO requires zero open high or critical privacy/security defects",
            )
        )

    if decision == "GO" and findings:
        findings.append(
            Finding(
                "invalid-go",
                "GO is not permitted while mandatory public-operations findings remain",
            )
        )

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    try:
        text = args.record.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR record-unreadable: {exc}", file=sys.stderr)
        return 1

    findings = validate_record(text)
    if findings:
        for finding in findings:
            print(f"ERROR {finding.code}: {finding.message}")
        print(f"INVALID: {len(findings)} finding(s)")
        return 1

    print("VALID: public operations activation record is internally complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
