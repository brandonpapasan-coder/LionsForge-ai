#!/usr/bin/env python3
"""Validate a completed LionsForge AI staging acceptance record.

The validator reads Markdown only. It never loads environment variables, credentials,
or external services. It exits 0 when the record is internally complete and consistent,
and exits 1 with deterministic findings otherwise.
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
    "Backend CI",
    "Frontend CI",
    "Security Gate",
    "Deployment Validation",
    "Staging Deploy",
    "Staging Frontend Deploy",
    "Authenticated smoke test",
    "OpenAI provider health",
    "Mentor schema validation",
}
REQUIRED_INFRASTRUCTURE = {
    "Kubernetes cluster and namespace",
    "Ingress, DNS, and HTTPS",
    "PostgreSQL connectivity",
    "Database backup and restore test",
    "GHCR image-pull access",
    "Error and latency observability",
    "Acceptance user provisioned",
}
REQUIRED_MANUAL_STEPS = {
    "Sign in and load Executive Dashboard",
    "Create research project and save notebook",
    "Create and reopen research session",
    "Open Mentor with resolved research context",
    "Receive complete evidence-first Mentor response",
    "Reopen and continue Mentor conversation",
    "Start and complete Education lesson",
    "Verify market-learning panels and disclaimers",
    "Sign out and sign back in",
    "Verify persisted research, mentor, education, and learning state",
    "Execute rollback verification",
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
        if not cells or cells[0] in {"Gate", "Check", "Step", "Severity", "---"}:
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

    sha = fields.get("Release candidate SHA", "")
    if not SHA_RE.fullmatch(sha):
        findings.append(Finding("invalid-sha", "Release candidate SHA must be exactly 40 lowercase hexadecimal characters"))

    for component in ("Backend", "Frontend"):
        digest = fields.get(f"{component} image digest", "")
        if not DIGEST_RE.fullmatch(digest):
            findings.append(
                Finding(
                    "invalid-image-digest",
                    f"{component} image digest must be sha256 followed by 64 lowercase hexadecimal characters",
                )
            )
        if fields.get(f"Running {component.lower()} image digest verified") != "Yes":
            findings.append(
                Finding(
                    "image-provenance-unverified",
                    f"Running {component.lower()} image digest verified must be Yes",
                )
            )

    for field in (
        "Staging deploy workflow run",
        "Staging frontend deploy workflow run",
        "Staging URL",
        "Acceptance date/time (UTC)",
        "Acceptance owner",
        "Previous deployable image SHA",
        "Database migration revision before deploy",
        "Database migration revision after deploy",
    ):
        if not fields.get(field):
            findings.append(Finding("missing-field", f"Required field is blank: {field}"))

    _require_passed(rows, REQUIRED_GATES, findings, "Automated validation")
    _require_passed(rows, REQUIRED_INFRASTRUCTURE, findings, "Infrastructure readiness")
    _require_passed(rows, REQUIRED_MANUAL_STEPS, findings, "Manual acceptance")

    rollback_fields = (
        "Previous image successfully identified",
        "Migration boundary reviewed",
        "Rollback command or workflow executed",
        "Service health restored after rollback",
        "Forward redeploy completed after rollback test",
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

    unresolved_critical = fields.get("Unresolved critical defects", "")
    unresolved_high = fields.get("Unresolved high-severity defects", "")
    if decision == "GO":
        allowed_zero = {"0", "None", "none"}
        if unresolved_critical not in allowed_zero:
            findings.append(Finding("blocking-defect", "GO requires zero unresolved critical defects"))
        if unresolved_high not in allowed_zero:
            findings.append(Finding("blocking-defect", "GO requires zero unresolved high-severity defects"))
        if "exact release candidate SHA and backend and frontend image digests" not in text:
            findings.append(Finding("missing-signoff", "GO requires the full image-provenance sign-off statement"))

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="Path to a completed staging acceptance Markdown record")
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

    print("VALID: staging acceptance record is internally complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
