#!/usr/bin/env python3
"""Validate a LionsForge AI Internal Alpha readiness Markdown record."""

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
PLACEHOLDERS = {
    "",
    "PENDING",
    "OPEN",
    "NOT VERIFIED",
    "NOT TESTED",
    "NOT APPROVED",
    "NOT APPLICABLE OR PENDING",
    "NOT APPLICABLE OR NOT VERIFIED",
    "NOT APPLICABLE OR NOT TESTED",
}
FAIL_STATUSES = PLACEHOLDERS | {"FAILED", "BLOCKED", "NO", "INCOMPLETE"}
REQUIRED_SECTIONS = (
    "## Current decision",
    "## 1. Candidate integrity",
    "## 2. Internal Alpha environment",
    "## 3. Integrated product journeys",
    "## 4. Cross-system controls",
    "## 5. Reliability, security, and operations",
    "## 6. Recovery and rollback",
    "## 7. Alpha cohort controls",
    "## 8. Final authorization",
    "## GO rule",
)
REQUIRED_BASE_FIELDS = (
    "Protected-main implementation merge",
    "Staging execution controls merge",
    "Pre-merge gate-clean candidate",
    "Backend image digest",
    "Frontend image digest",
    "Review owner role",
    "Review date",
    "Decision",
)


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


def _normalize(value: str) -> str:
    return value.strip().strip("`").strip("*").strip()


def _fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = FIELD_RE.match(line.strip())
        if match:
            fields[match.group(1).strip()] = _normalize(match.group(2))
    return fields


def _rows(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        match = TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        cells = [_normalize(cell) for cell in match.group(1).split("|")]
        if not cells or all(set(cell) <= {"-", ":"} for cell in cells if cell):
            continue
        if cells[0] in {
            "Control",
            "Dependency",
            "Journey",
            "Integration control",
            "Gate",
            "Exercise",
            "Blocker",
            "Approval",
        }:
            continue
        rows.append(cells)
    return rows


def _record_incomplete(value: str) -> bool:
    normalized = _normalize(value).upper()
    return normalized in FAIL_STATUSES or normalized.startswith("PENDING")


def _first_field(fields: dict[str, str], *names: str) -> str:
    for name in names:
        value = fields.get(name, "")
        if value:
            return value
    return ""


def validate_record(text: str) -> list[Finding]:
    lines = text.splitlines()
    fields = _fields(lines)
    rows = _rows(lines)
    findings: list[Finding] = []

    for section in REQUIRED_SECTIONS:
        if section not in lines:
            findings.append(Finding("missing-section", f"Required section is missing: {section}"))

    for field in REQUIRED_BASE_FIELDS:
        if field not in fields:
            findings.append(Finding("missing-field", f"Required baseline field is missing: {field}"))

    decision = fields.get("Decision", "")
    if decision not in {"GO", "NO-GO"}:
        findings.append(Finding("invalid-decision", "Decision must be GO or NO-GO"))
        return findings

    if decision == "NO-GO":
        return findings

    candidate_sha = _first_field(
        fields,
        "Candidate commit SHA",
        "Protected-main implementation merge",
    )
    if not SHA_RE.fullmatch(candidate_sha):
        findings.append(Finding("invalid-sha", "GO requires an exact 40-character candidate SHA"))

    for component in ("backend", "frontend"):
        digest = _first_field(
            fields,
            f"Candidate {component} image digest",
            f"{component.title()} image digest",
        )
        if not DIGEST_RE.fullmatch(digest):
            findings.append(
                Finding(
                    "invalid-image-digest",
                    f"GO requires an immutable {component} sha256 image digest",
                )
            )

    for field in ("Review owner role", "Review date"):
        if _record_incomplete(fields.get(field, "")):
            findings.append(Finding("missing-field", f"GO requires completed field: {field}"))

    for cells in rows:
        name = cells[0]
        values = cells[1:]
        if any(_record_incomplete(value) for value in values):
            findings.append(Finding("incomplete-control", f"GO control is incomplete: {name}"))

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("-") or ":" not in stripped:
            continue
        key, value = stripped[1:].split(":", 1)
        if _record_incomplete(value):
            findings.append(
                Finding("incomplete-field", f"GO field is incomplete: {key.strip()}")
            )

    if "| OPEN |" in text or "| BLOCKING |" in text:
        findings.append(Finding("open-blocker", "GO cannot include open blocking items"))

    required_signoff = (
        "exact candidate SHA and immutable backend and frontend image digests recorded above"
    )
    if required_signoff not in text:
        findings.append(
            Finding(
                "missing-signoff",
                "GO requires the Internal Alpha provenance sign-off statement",
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

    print("VALID: Internal Alpha readiness decision is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
