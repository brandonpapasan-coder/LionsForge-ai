#!/usr/bin/env python3
"""Validate a completed LionsForge AI production acceptance record.

The validator reads Markdown only. It never loads credentials, environment secrets,
or external services. It exits 0 only when the record is internally complete and
consistent with the production release gates.
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
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")

REQUIRED_GATES = {
    "Staging GO",
    "Backend CI",
    "Frontend CI",
    "Security Gate",
    "Deployment Validation",
    "Production preflight",
    "Backend production deploy",
    "Frontend production deploy",
    "Authenticated API smoke",
    "Frontend HTTPS smoke",
}

REQUIRED_OPERATIONS = {
    "Kubernetes production environment",
    "PostgreSQL connectivity and encryption",
    "DNS and valid HTTPS",
    "Registry image-pull access",
    "Resource requests and limits",
    "Capacity or autoscaling controls",
    "Backup retention",
    "Restore exercise",
    "Centralized logs",
    "Availability, error, latency, and database alerts",
    "OpenAI usage and budget alerts",
    "Production admin and acceptance accounts",
    "Least-privilege access review",
}

REQUIRED_JOURNEYS = {
    "Controlled registration or invitation",
    "Sign in and sign out",
    "Session and persisted-state recovery",
    "Dashboard",
    "Create private investigation",
    "Add claims and evidence",
    "Record validation judgment",
    "View education-gap recommendations",
    "Mentor healthy response",
    "Mentor unavailable/fallback behavior",
    "Education lesson and adaptive assessment",
    "Owner isolation",
    "Answer-key privacy",
    "Support request path",
    "Account deletion and retention workflow",
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
        if not cells or cells[0] in {"Gate", "Check", "Journey", "Severity", "---"}:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells if cell):
            continue
        rows[cells[0]] = cells[1:]
    return rows


def _require_passed(rows: dict[str, list[str]], names: set[str], findings: list[Finding], group: str) -> None:
    for name in sorted(names):
        cells = rows.get(name)
        if cells is None:
            findings.append(Finding("missing-row", f"{group} row is missing: {name}"))
            continue
        result = cells[0] if cells else ""
        if result != "Passed":
            findings.append(Finding("incomplete-check", f"{group} must be Passed: {name} (found {result or 'blank'})"))


def validate_record(text: str) -> list[Finding]:
    lines = text.splitlines()
    fields = _field_map(lines)
    rows = _table_rows(lines)
    findings: list[Finding] = []

    release_sha = fields.get("Release SHA", "")
    rollback_sha = fields.get("Rollback SHA", "")
    if not SHA_RE.fullmatch(release_sha):
        findings.append(Finding("invalid-sha", "Release SHA must be exactly 40 lowercase hexadecimal characters"))
    if not SHA_RE.fullmatch(rollback_sha):
        findings.append(Finding("invalid-sha", "Rollback SHA must be exactly 40 lowercase hexadecimal characters"))
    if release_sha and rollback_sha and release_sha == rollback_sha:
        findings.append(Finding("invalid-rollback", "Release SHA and rollback SHA must differ"))

    for component in ("Backend", "Frontend"):
        digest = fields.get(f"{component} image digest", "")
        if not DIGEST_RE.fullmatch(digest):
            findings.append(Finding("invalid-image-digest", f"{component} image digest must be sha256 followed by 64 lowercase hexadecimal characters"))
        if fields.get(f"Running {component.lower()} digest verified") != "Yes":
            findings.append(Finding("image-provenance-unverified", f"Running {component.lower()} digest verified must be Yes"))

    for field in (
        "Staging GO evidence",
        "Backend deploy workflow run",
        "Frontend deploy workflow run",
        "Production API URL",
        "Production web URL",
        "Release owner",
        "Approval owner",
        "Release date/time (UTC)",
        "Migration revision before deploy",
        "Migration revision after deploy",
    ):
        if not fields.get(field):
            findings.append(Finding("missing-field", f"Required field is blank: {field}"))

    for url_field in ("Production API URL", "Production web URL"):
        value = fields.get(url_field, "")
        if value and not value.startswith("https://"):
            findings.append(Finding("invalid-url", f"{url_field} must be an HTTPS URL"))

    _require_passed(rows, REQUIRED_GATES, findings, "Required gate")
    _require_passed(rows, REQUIRED_OPERATIONS, findings, "Infrastructure and operations")
    _require_passed(rows, REQUIRED_JOURNEYS, findings, "Critical user journey")

    rollback_fields = (
        "Previous backend and frontend images identified",
        "Migration boundary reviewed",
        "Backend rollback executed",
        "Frontend rollback executed",
        "Service health restored",
        "Forward redeploy completed",
    )
    for field in rollback_fields:
        if fields.get(field) != "Yes":
            findings.append(Finding("rollback-incomplete", f"Rollback evidence must be Yes: {field}"))

    decision = fields.get("Decision", "")
    if decision not in {"GO", "NO-GO"}:
        findings.append(Finding("invalid-decision", "Decision must be GO or NO-GO"))
    if not fields.get("Decision owner"):
        findings.append(Finding("missing-field", "Required field is blank: Decision owner"))
    if not fields.get("Decision timestamp (UTC)"):
        findings.append(Finding("missing-field", "Required field is blank: Decision timestamp (UTC)"))

    if decision == "GO":
        allowed_zero = {"0", "None", "none"}
        if fields.get("Unresolved critical defects", "") not in allowed_zero:
            findings.append(Finding("blocking-defect", "GO requires zero unresolved critical defects"))
        if fields.get("Unresolved high-severity defects", "") not in allowed_zero:
            findings.append(Finding("blocking-defect", "GO requires zero unresolved high-severity defects"))
        required_signoff = "exact release and rollback SHAs and backend and frontend image digests"
        if required_signoff not in text:
            findings.append(Finding("missing-signoff", "GO requires the full production provenance sign-off statement"))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="Path to a completed production acceptance Markdown record")
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

    print("VALID: production acceptance record is internally complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
