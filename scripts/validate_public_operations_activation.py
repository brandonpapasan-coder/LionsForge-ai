#!/usr/bin/env python3
"""Validate a completed LionsForge AI public operations activation record."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FIELD_RE = re.compile(r"^- ([^:]+):\s*(.*)$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")

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
                "Release candidate SHA must be exactly 40 lowercase hexadecimal "
                "characters",
            )
        )

    decision = fields.get("Decision", "")
    if decision not in {"GO", "NO-GO"}:
        findings.append(Finding("invalid-decision", "Decision must be GO or NO-GO"))

    for field in (
        "Record owner role",
        "Review date",
        "Intended effective date",
        "Public legal entity name",
        "Governing-law and venue language approved",
        "Supported launch jurisdictions",
        "Age eligibility and parental-consent position",
        "Jurisdiction-specific privacy-rights matrix reference",
        "Subprocessor and AI-provider disclosure reference",
        "Support response target",
        "Privacy-request response target",
        "Security-report acknowledgment target",
        "Abuse-report acknowledgment target",
        "After-hours critical incident coverage",
        "Escalation owner role",
    ):
        value = fields.get(field, "")
        if not value or value in {"PENDING", "NOT VERIFIED", "NOT TESTED"}:
            findings.append(
                Finding("missing-field", f"Required field is incomplete: {field}")
            )

    _require_rows(rows, REQUIRED_POLICY_SURFACES, findings, "Policy")
    _require_rows(rows, REQUIRED_CHANNELS, findings, "Monitored channel")
    _require_rows(rows, REQUIRED_RETENTION_CLASSES, findings, "Retention")
    _require_rows(rows, REQUIRED_WORKFLOWS, findings, "Workflow")
    _require_rows(rows, REQUIRED_APPROVALS, findings, "Approval")

    for name in REQUIRED_POLICY_SURFACES:
        cells = rows.get(name, [])
        if len(cells) < 5 or cells[4] != "APPROVED":
            findings.append(
                Finding("policy-unapproved", f"Policy must be APPROVED: {name}")
            )
        if any(value in {"", "PENDING", "NOT APPROVED"} for value in cells[:4]):
            findings.append(
                Finding("policy-incomplete", f"Policy metadata is incomplete: {name}")
            )

    for name in REQUIRED_CHANNELS:
        cells = rows.get(name, [])
        if len(cells) < 4 or cells[2] != "VERIFIED":
            findings.append(
                Finding(
                    "channel-unverified",
                    f"Channel monitoring must be VERIFIED: {name}",
                )
            )
        if any(value in {"", "PENDING", "NOT VERIFIED"} for value in cells[:4]):
            findings.append(
                Finding(
                    "channel-incomplete", f"Channel metadata is incomplete: {name}"
                )
            )

    for name in REQUIRED_RETENTION_CLASSES:
        cells = rows.get(name, [])
        if len(cells) < 4 or cells[3] != "APPROVED":
            findings.append(
                Finding(
                    "retention-unapproved",
                    f"Retention configuration must be APPROVED: {name}",
                )
            )
        if any(value in {"", "PENDING", "NOT APPROVED"} for value in cells[:4]):
            findings.append(
                Finding(
                    "retention-incomplete",
                    f"Retention metadata is incomplete: {name}",
                )
            )

    for name in REQUIRED_WORKFLOWS:
        cells = rows.get(name, [])
        if len(cells) < 4 or cells[3] != "PASSED":
            findings.append(
                Finding("workflow-untested", f"Workflow must be PASSED: {name}")
            )
        if any(value in {"", "PENDING", "NOT TESTED"} for value in cells[:4]):
            findings.append(
                Finding(
                    "workflow-incomplete",
                    f"Workflow evidence is incomplete: {name}",
                )
            )

    for name in REQUIRED_APPROVALS:
        cells = rows.get(name, [])
        if len(cells) < 3 or cells[2] != "APPROVED":
            findings.append(
                Finding(
                    "approval-missing", f"Final approval must be APPROVED: {name}"
                )
            )
        if any(value in {"", "PENDING", "NOT APPROVED"} for value in cells[:3]):
            findings.append(
                Finding(
                    "approval-incomplete",
                    f"Approval metadata is incomplete: {name}",
                )
            )

    for field in (
        "Log-redaction review completed",
        "Secrets and credentials excluded from logs",
        "Private prompts, evidence, education records, and support content excluded or minimized",
        "Analytics and cookie inventory completed",
    ):
        if fields.get(field) not in {"YES", "VERIFIED"}:
            findings.append(
                Finding(
                    "privacy-control-incomplete",
                    f"Privacy control is incomplete: {field}",
                )
            )

    if fields.get("Open high or critical privacy/security defects", "") not in {
        "0",
        "None",
        "none",
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
