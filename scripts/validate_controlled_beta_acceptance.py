#!/usr/bin/env python3
"""Validate a completed LionsForge AI controlled beta acceptance record.

The validator reads Markdown only. It never loads credentials, private tester data,
application content, or external services. It exits 0 only when the record is
internally complete and consistent. A valid record is not launch authorization.
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
NONNEGATIVE_INT_RE = re.compile(r"^\d+$")
DECISION_RE = re.compile(r"^- \[([ xX])\]\s+(GO|CONDITIONAL GO|NO-GO)\b")

REQUIRED_ENTRY_GATES = {
    "Staging acceptance approved",
    "Production readiness approved",
    "Public policies and support processes live",
    "Backup and restore evidence current",
    "Rollback evidence current",
    "Monitoring and alerts verified",
    "No unresolved severity-1 or severity-2 defects",
    "Invitation or registration cap enforced",
    "Usage and budget limits enforced",
}

REQUIRED_JOURNEYS = {
    "Invitation/approved registration",
    "Authentication/session recovery",
    "Investigation privacy and creation",
    "Claims and evidence",
    "Validation and provenance ledger",
    "Education recommendations",
    "Adaptive assessment",
    "Mentor interaction",
    "Support request",
    "Privacy/deletion request intake",
    "Logout/revoked access",
}

REQUIRED_EXERCISES = {
    "AI provider timeout",
    "AI provider unavailable",
    "API outage alert",
    "Frontend outage alert",
    "Database failure alert",
    "Elevated error-rate alert",
    "Budget threshold alert",
    "Rollback",
    "Isolated restore verification",
}

ALLOWED_RESULTS = {"Passed", "Failed", "Blocked", "Not run"}
REQUIRED_NONBLANK_FIELDS = {
    "Deployment date/time",
    "Operator",
    "Environment",
    "Maximum invited users",
    "Accepted users",
    "Per-user daily AI request limit",
    "Aggregate daily AI budget",
    "Abuse threshold",
    "Support owner",
    "Incident owner",
    "Legal approver",
    "Security approver",
    "Operations approver",
    "Product approver",
    "Evidence links or identifiers",
    "Beta start",
    "Beta end",
    "Peak concurrent users",
    "Availability",
    "API latency summary",
    "Frontend latency summary",
    "Error-rate summary",
    "AI requests",
    "AI cost total",
    "AI cost per active user",
    "Support reports",
    "Severity-1 incidents",
    "Severity-2 incidents",
    "Other defects",
    "Decision rationale",
    "Legal approval",
    "Security approval",
    "Operations approval",
    "Product approval",
    "Owner approval",
    "Decision date/time",
}
NUMERIC_FIELDS = {
    "Maximum invited users",
    "Accepted users",
    "Per-user daily AI request limit",
    "Peak concurrent users",
    "AI requests",
    "Support reports",
    "Severity-1 incidents",
    "Severity-2 incidents",
    "Other defects",
}
PRIVATE_CONTENT_PATTERNS = {
    "credential": re.compile(r"(?i)\b(password|secret|api[_ -]?key|access[_ -]?token)\b\s*[:=]\s*\S+"),
    "private-tester": re.compile(r"(?i)\btester\s+(email|name|identity)\b\s*[:=]\s*\S+"),
    "answer-key": re.compile(r"(?i)\banswer\s*key\b\s*[:=]"),
    "prompt-content": re.compile(r"(?i)\b(private\s+prompt|research\s+content|hidden\s+assessment)\b\s*[:=]"),
}


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


def _normalize(value: str) -> str:
    return value.strip().strip("`").strip()


def _field_map(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for index, line in enumerate(lines):
        match = FIELD_RE.match(line.strip())
        if match:
            fields[match.group(1).strip()] = _normalize(match.group(2))
            continue
        if line.strip().endswith(":") and index + 1 < len(lines):
            key = line.strip()[:-1]
            following = _normalize(lines[index + 1])
            if following and not following.startswith("#"):
                fields[key] = following
    return fields


def _table_rows(lines: list[str]) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in lines:
        match = TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        cells = [_normalize(cell) for cell in match.group(1).split("|")]
        if not cells or cells[0] in {"Journey", "Exercise", "---"}:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells if cell):
            continue
        rows[cells[0]] = cells[1:]
    return rows


def _checked_items(lines: list[str]) -> dict[str, bool]:
    items: dict[str, bool] = {}
    for line in lines:
        match = CHECKBOX_RE.match(line.strip())
        if match:
            items[match.group(2).strip()] = match.group(1).lower() == "x"
    return items


def _selected_decisions(lines: list[str]) -> list[str]:
    selected: list[str] = []
    for line in lines:
        match = DECISION_RE.match(line.strip())
        if match and match.group(1).lower() == "x":
            selected.append(match.group(2))
    return selected


def _require_rows(
    rows: dict[str, list[str]], names: set[str], findings: list[Finding], group: str
) -> None:
    for name in sorted(names):
        cells = rows.get(name)
        if cells is None:
            findings.append(Finding("missing-row", f"{group} row is missing: {name}"))
            continue
        result = cells[0] if cells else ""
        evidence = cells[1] if len(cells) > 1 else ""
        if result not in ALLOWED_RESULTS:
            findings.append(
                Finding("invalid-result", f"{group} result is unsupported: {name} ({result or 'blank'})")
            )
        if not evidence:
            findings.append(Finding("missing-evidence", f"{group} evidence is blank: {name}"))


def validate_record(text: str) -> list[Finding]:
    lines = text.splitlines()
    fields = _field_map(lines)
    rows = _table_rows(lines)
    checks = _checked_items(lines)
    decisions = _selected_decisions(lines)
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
        digest = fields.get(f"{component} image digest", "")
        if not DIGEST_RE.fullmatch(digest):
            findings.append(
                Finding("invalid-image-digest", f"{component} image digest must be sha256 followed by 64 lowercase hexadecimal characters")
            )

    for field in sorted(REQUIRED_NONBLANK_FIELDS):
        if not fields.get(field):
            findings.append(Finding("missing-field", f"Required field is blank: {field}"))

    for field in sorted(NUMERIC_FIELDS):
        value = fields.get(field, "")
        if value and not NONNEGATIVE_INT_RE.fullmatch(value):
            findings.append(Finding("invalid-number", f"{field} must be a nonnegative integer"))

    maximum = fields.get("Maximum invited users", "")
    accepted = fields.get("Accepted users", "")
    if NONNEGATIVE_INT_RE.fullmatch(maximum) and NONNEGATIVE_INT_RE.fullmatch(accepted):
        if int(accepted) > int(maximum):
            findings.append(Finding("invalid-cap", "Accepted users cannot exceed maximum invited users"))

    for gate in sorted(REQUIRED_ENTRY_GATES):
        if gate not in checks:
            findings.append(Finding("missing-gate", f"Entry-gate checkbox is missing: {gate}"))
        elif not checks[gate]:
            findings.append(Finding("incomplete-gate", f"Entry gate must be checked: {gate}"))

    _require_rows(rows, REQUIRED_JOURNEYS, findings, "Critical journey")
    _require_rows(rows, REQUIRED_EXERCISES, findings, "Resilience exercise")

    if len(decisions) != 1:
        findings.append(Finding("invalid-decision", "Exactly one decision checkbox must be selected"))
        decision = ""
    else:
        decision = decisions[0]

    failing_results = {
        name: cells[0]
        for name, cells in rows.items()
        if cells and cells[0] in {"Failed", "Blocked", "Not run"}
    }
    severity_1 = fields.get("Severity-1 incidents", "")
    severity_2 = fields.get("Severity-2 incidents", "")
    conditions = fields.get("Conditions and deadlines", "")

    if decision == "GO":
        if failing_results:
            findings.append(Finding("decision-conflict", "GO requires every journey and resilience exercise to be Passed"))
        if severity_1 not in {"0"} or severity_2 not in {"0"}:
            findings.append(Finding("decision-conflict", "GO requires zero severity-1 and severity-2 incidents"))
        if conditions and conditions.lower() not in {"none", "n/a", "not applicable"}:
            findings.append(Finding("decision-conflict", "GO cannot include unresolved conditions or deadlines"))
    elif decision == "CONDITIONAL GO":
        if not conditions or conditions.lower() in {"none", "n/a", "not applicable"}:
            findings.append(Finding("missing-condition", "CONDITIONAL GO requires explicit conditions and deadlines"))
        if severity_1 not in {"0"}:
            findings.append(Finding("decision-conflict", "CONDITIONAL GO requires zero severity-1 incidents"))
        if any(result in {"Failed", "Blocked"} for result in failing_results.values()):
            findings.append(Finding("decision-conflict", "CONDITIONAL GO cannot include Failed or Blocked required checks"))
    elif decision == "NO-GO":
        if not fields.get("Decision rationale"):
            findings.append(Finding("missing-field", "NO-GO requires a decision rationale"))

    for code, pattern in PRIVATE_CONTENT_PATTERNS.items():
        if pattern.search(text):
            findings.append(Finding("private-content", f"Record appears to contain prohibited private content: {code}"))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="Path to a completed controlled beta acceptance Markdown record")
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

    print("VALID: controlled beta acceptance record is internally complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
