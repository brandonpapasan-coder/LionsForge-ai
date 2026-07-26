#!/usr/bin/env python3
"""Validate a completed LionsForge AI general-availability decision record.

This validator reads Markdown only. It checks record structure and internal
consistency; it does not verify live evidence or authorize launch.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FIELD_RE = re.compile(r"^- ([^:]+):\s*(.*)$")
CHECKBOX_RE = re.compile(r"^- \[([ xX])\]\s+(.+)$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
DECISION_RE = re.compile(r"^- \[([ xX])\]\s+(GO|NO-GO)\b")
NONNEGATIVE_INT_RE = re.compile(r"^\d+$")
MONEY_RE = re.compile(r"^\$?\d+(?:\.\d{1,2})?$")

REQUIRED_GATES = {
    "Production acceptance is approved for this exact release and image digests",
    "Public policies, consent, deletion, retention, support, abuse, and security-reporting workflows are live",
    "Controlled beta completed on this exact release candidate or an explicitly validated successor",
    "Running backend and frontend image digests match the approved immutable digests",
    "Backup and isolated restore evidence is current",
    "Rollback evidence is current",
    "Monitoring and launch-critical alerts are verified",
    "Registration, usage, abuse, and budget limits are enforced",
    "Support and incident owners are on duty",
    "No unresolved severity-1 or severity-2 incidents remain",
    "No unresolved critical or high-severity defects remain",
    "No expired exception remains open",
}

REQUIRED_CONTROLS = {
    "HTTPS API and web availability",
    "Authentication and session recovery",
    "Owner isolation and privacy",
    "Investigation, claims, and evidence workflow",
    "Validation and provenance workflow",
    "Education and adaptive assessment",
    "Mentor provider-failure behavior",
    "Account deletion and retention workflow",
    "Support and abuse-reporting workflow",
    "Security-reporting workflow",
    "Monitoring and alert delivery",
    "Rollback exercise",
    "Isolated restore verification",
    "Budget-threshold enforcement",
}

REQUIRED_FIELDS = {
    "Deployment environment",
    "Proposed GA date/time (UTC)",
    "Release owner",
    "Operations owner",
    "Production acceptance evidence",
    "Public-operations activation evidence",
    "Controlled-beta acceptance evidence",
    "Candidate ancestry evidence",
    "Running backend digest evidence",
    "Running frontend digest evidence",
    "Registration mode",
    "Abuse threshold",
    "Support owner",
    "Incident owner",
    "Privacy owner",
    "Security owner",
    "Rollback authority",
    "Availability",
    "API latency summary",
    "Frontend latency summary",
    "Error-rate summary",
    "Open-risk summary",
    "Exception register evidence",
    "Legal approval",
    "Privacy approval",
    "Security approval",
    "Operations approval",
    "Support approval",
    "Product approval",
    "Executive owner approval",
    "Decision owner",
    "Decision date/time (UTC)",
}

COUNT_FIELDS = {
    "Maximum registered users",
    "Per-user daily AI request limit",
    "Beta active users",
    "Peak concurrent users",
    "AI requests",
    "Support reports",
    "Severity-1 incidents",
    "Severity-2 incidents",
    "Unresolved critical defects",
    "Unresolved high-severity defects",
    "Other unresolved defects",
    "Open exceptions",
    "Expired exceptions",
}

MONEY_FIELDS = {
    "Aggregate daily AI budget (USD)",
    "AI cost total (USD)",
    "AI cost per active user (USD)",
}

PROHIBITED_PATTERNS = {
    "credential": re.compile(r"\b(password|secret|api[_ -]?key|access[_ -]?token|bearer token)\b", re.I),
    "private-user-content": re.compile(r"\b(tester email|private prompt|support record contents?|deletion-request contents?|answer key|hidden assessment)\b", re.I),
    "secret-value": re.compile(r"\b(sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9]{8,})\b"),
}


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


def _normalize(value: str) -> str:
    return value.strip().strip("`").strip()


def _field_map(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = FIELD_RE.match(line.strip())
        if match:
            fields[match.group(1).strip()] = _normalize(match.group(2))
    return fields


def _table_rows(lines: list[str]) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in lines:
        match = TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        cells = [_normalize(cell) for cell in match.group(1).split("|")]
        if not cells or cells[0] in {"Control", "---"}:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells if cell):
            continue
        rows[cells[0]] = cells[1:]
    return rows


def _selected_decisions(lines: list[str]) -> list[str]:
    selected: list[str] = []
    for line in lines:
        match = DECISION_RE.match(line.strip())
        if match and match.group(1).lower() == "x":
            selected.append(match.group(2))
    return selected


def _section_text(text: str, heading: str, next_heading: str | None = None) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    end = text.find(next_heading, start) if next_heading else len(text)
    return text[start:end if end >= 0 else len(text)].strip()


def validate_record(text: str) -> list[Finding]:
    lines = text.splitlines()
    fields = _field_map(lines)
    rows = _table_rows(lines)
    findings: list[Finding] = []

    release_sha = fields.get("Release SHA", "")
    rollback_sha = fields.get("Previous rollback SHA", "")
    if not SHA_RE.fullmatch(release_sha):
        findings.append(Finding("invalid-sha", "Release SHA must be exactly 40 lowercase hexadecimal characters"))
    if not SHA_RE.fullmatch(rollback_sha):
        findings.append(Finding("invalid-sha", "Previous rollback SHA must be exactly 40 lowercase hexadecimal characters"))
    if release_sha and rollback_sha and release_sha == rollback_sha:
        findings.append(Finding("invalid-rollback", "Release SHA and previous rollback SHA must differ"))

    for component in ("Backend", "Frontend"):
        value = fields.get(f"{component} image digest", "")
        if not DIGEST_RE.fullmatch(value):
            findings.append(Finding("invalid-image-digest", f"{component} image digest must be sha256 followed by 64 lowercase hexadecimal characters"))

    for field in sorted(REQUIRED_FIELDS):
        if not fields.get(field):
            findings.append(Finding("missing-field", f"Required field is blank: {field}"))

    for field in sorted(COUNT_FIELDS):
        value = fields.get(field, "")
        if not NONNEGATIVE_INT_RE.fullmatch(value):
            findings.append(Finding("invalid-number", f"{field} must be a nonnegative integer"))

    for field in sorted(MONEY_FIELDS):
        value = fields.get(field, "")
        if not MONEY_RE.fullmatch(value):
            findings.append(Finding("invalid-money", f"{field} must be a nonnegative USD amount"))

    checkboxes: dict[str, bool] = {}
    for line in lines:
        match = CHECKBOX_RE.match(line.strip())
        if match:
            checkboxes[match.group(2).strip()] = match.group(1).lower() == "x"
    for gate in sorted(REQUIRED_GATES):
        if gate not in checkboxes:
            findings.append(Finding("missing-gate", f"Critical exit gate is missing: {gate}"))
        elif not checkboxes[gate]:
            findings.append(Finding("incomplete-gate", f"Critical exit gate must be checked: {gate}"))

    evidence_block = _section_text(text, "Evidence links or identifiers:", "## Operational evidence")
    if not evidence_block:
        findings.append(Finding("missing-evidence", "Critical exit-gate evidence links or identifiers are required"))

    for control in sorted(REQUIRED_CONTROLS):
        cells = rows.get(control)
        if cells is None:
            findings.append(Finding("missing-row", f"Operational control row is missing: {control}"))
            continue
        result = cells[0] if len(cells) > 0 else ""
        evidence = cells[1] if len(cells) > 1 else ""
        if result not in {"Passed", "Failed", "Blocked"}:
            findings.append(Finding("invalid-result", f"Operational control result must be Passed, Failed, or Blocked: {control}"))
        if not evidence:
            findings.append(Finding("missing-evidence", f"Operational control evidence is required: {control}"))

    decisions = _selected_decisions(lines)
    if len(decisions) != 1:
        findings.append(Finding("invalid-decision", "Select exactly one decision: GO or NO-GO"))
        decision = ""
    else:
        decision = decisions[0]

    rationale = _section_text(text, "Decision rationale:", "- Decision owner:")
    if not rationale:
        findings.append(Finding("missing-rationale", "Decision rationale is required"))

    failed_controls = [name for name in REQUIRED_CONTROLS if rows.get(name, [""])[0] != "Passed"]
    zero_fields = (
        "Severity-1 incidents",
        "Severity-2 incidents",
        "Unresolved critical defects",
        "Unresolved high-severity defects",
        "Expired exceptions",
    )
    if decision == "GO":
        for field in zero_fields:
            if fields.get(field) != "0":
                findings.append(Finding("decision-conflict", f"GO requires {field} to be 0"))
        if failed_controls:
            findings.append(Finding("decision-conflict", "GO requires every operational control to be Passed"))
        if fields.get("Blocker rationale", "") not in {"", "None", "none", "N/A", "n/a"}:
            findings.append(Finding("decision-conflict", "GO cannot include a blocker rationale"))
    elif decision == "NO-GO":
        if not fields.get("Blocker rationale"):
            findings.append(Finding("missing-blocker", "NO-GO requires a blocker rationale"))
        if not fields.get("Blocker owner"):
            findings.append(Finding("missing-blocker", "NO-GO requires a blocker owner"))

    max_users = fields.get("Maximum registered users", "")
    beta_users = fields.get("Beta active users", "")
    if max_users.isdigit() and beta_users.isdigit() and int(beta_users) > int(max_users):
        findings.append(Finding("invalid-cap", "Beta active users cannot exceed maximum registered users"))

    for code, pattern in PROHIBITED_PATTERNS.items():
        if pattern.search(text):
            findings.append(Finding("private-content", f"Record contains prohibited or apparent private content: {code}"))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="Path to a completed GA decision Markdown record")
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
    print("VALID: general-availability decision record is internally complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
