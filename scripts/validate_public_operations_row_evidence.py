#!/usr/bin/env python3
"""Validate row-level dates and evidence in a public operations record."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

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

POLICY_ROWS = {
    "Privacy Notice",
    "Terms of Service",
    "Responsible AI disclosure",
    "Data retention and deletion policy",
    "Acceptable use and abuse reporting",
}
CHANNEL_ROWS = {
    "General support",
    "Privacy requests",
    "Security reports",
    "Abuse reports",
}
WORKFLOW_ROWS = {
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
APPROVAL_ROWS = {
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
    fields: dict[str, str] = {}
    for line in lines:
        match = FIELD_RE.match(line.strip())
        if match:
            fields[match.group(1).strip()] = _normalize(match.group(2))
    return fields


def _rows(lines: list[str]) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    headers = {"Surface", "Function", "Data class", "Workflow", "Approval", "---"}
    for line in lines:
        match = TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        cells = [_normalize(cell) for cell in match.group(1).split("|")]
        if not cells or cells[0] in headers:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells if cell):
            continue
        rows[cells[0]] = cells[1:]
    return rows


def _parse_date(value: str, *, label: str, findings: list[Finding]) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        findings.append(Finding("invalid-row-date", f"{label} must use YYYY-MM-DD"))
        return None


def _require_reference(value: str, *, label: str, findings: list[Finding]) -> None:
    if _is_placeholder(value) or len(value.strip()) < 3:
        findings.append(Finding("invalid-row-reference", f"Evidence reference is incomplete: {label}"))


def validate_record(text: str) -> list[Finding]:
    lines = text.splitlines()
    fields = _fields(lines)
    rows = _rows(lines)
    findings: list[Finding] = []

    review_date = _parse_date(
        fields.get("Review date", ""), label="Review date", findings=findings
    )
    launch_date = _parse_date(
        fields.get("Intended effective date", ""),
        label="Intended effective date",
        findings=findings,
    )

    for name in sorted(POLICY_ROWS):
        cells = rows.get(name, [])
        if len(cells) < 5:
            findings.append(Finding("missing-row-evidence", f"Policy row is incomplete: {name}"))
            continue
        effective = _parse_date(
            cells[1], label=f"Policy effective date for {name}", findings=findings
        )
        if effective and launch_date and effective > launch_date:
            findings.append(
                Finding(
                    "policy-effective-after-launch",
                    f"Policy becomes effective after intended launch: {name}",
                )
            )

    for name in sorted(CHANNEL_ROWS):
        cells = rows.get(name, [])
        if len(cells) < 4:
            findings.append(Finding("missing-row-evidence", f"Channel row is incomplete: {name}"))
            continue
        _require_reference(
            cells[3], label=f"Channel test evidence for {name}", findings=findings
        )

    for name in sorted(WORKFLOW_ROWS):
        cells = rows.get(name, [])
        if len(cells) < 4:
            findings.append(Finding("missing-row-evidence", f"Workflow row is incomplete: {name}"))
            continue
        tested = _parse_date(cells[0], label=f"Workflow test date for {name}", findings=findings)
        if tested and review_date and tested > review_date:
            findings.append(
                Finding(
                    "workflow-tested-after-review",
                    f"Workflow test date is after review date: {name}",
                )
            )
        _require_reference(
            cells[2], label=f"Workflow evidence for {name}", findings=findings
        )

    for name in sorted(APPROVAL_ROWS):
        cells = rows.get(name, [])
        if len(cells) < 3:
            findings.append(Finding("missing-row-evidence", f"Approval row is incomplete: {name}"))
            continue
        approved = _parse_date(cells[1], label=f"Approval date for {name}", findings=findings)
        if approved and review_date and approved > review_date:
            findings.append(
                Finding(
                    "approval-after-review",
                    f"Approval date is after review date: {name}",
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
        print(f"INVALID: {len(findings)} row-evidence finding(s)")
        return 1

    print("VALID: public operations row evidence is internally complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
