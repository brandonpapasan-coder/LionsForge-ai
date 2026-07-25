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
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
RUN_URL_RE = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/actions/runs/([1-9][0-9]*)$"
)
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FIELD_RE = re.compile(r"^- ([^:]+):\s*(.*)$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
PLACEHOLDER_VALUES = {"", "-", "n/a", "none", "owner", "pending", "ref", "tbd", "todo"}
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
    "Create or review evidence and verify knowledge-quality update",
    "Sign out and sign back in",
    "Verify persisted research, Mentor, education, evidence, and knowledge state",
    "Verify legacy finance surfaces are absent by default",
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


def _require_passed(
    rows: dict[str, list[str]], names: set[str], findings: list[Finding], group: str
) -> None:
    for name in sorted(names):
        cells = rows.get(name)
        if cells is None:
            findings.append(Finding("missing-row", f"{group} row is missing: {name}"))
            continue
        result = cells[0] if cells else ""
        if result != "Passed":
            findings.append(
                Finding(
                    "incomplete-check",
                    f"{group} must be Passed: {name} (found {result or 'blank'})",
                )
            )
            continue
        evidence = cells[1] if len(cells) > 1 else ""
        if evidence.casefold() in PLACEHOLDER_VALUES:
            findings.append(
                Finding(
                    "placeholder-evidence",
                    f"{group} requires concrete evidence: {name}",
                )
            )


def _parse_utc_timestamp(value: str, field: str, findings: list[Finding]) -> datetime | None:
    if not UTC_TIMESTAMP_RE.fullmatch(value):
        findings.append(
            Finding(
                "invalid-timestamp",
                f"{field} must be strict UTC RFC3339 in YYYY-MM-DDTHH:MM:SSZ form",
            )
        )
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        findings.append(Finding("invalid-timestamp", f"{field} is not a valid calendar timestamp"))
        return None


def _validate_staging_url(value: str, findings: list[Finding]) -> None:
    parsed = urlparse(value)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        findings.append(Finding("invalid-staging-url", "Staging URL must be an HTTPS origin without credentials"))
        return
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        findings.append(Finding("invalid-staging-url", "Staging URL must not contain a path, query, or fragment"))
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        findings.append(Finding("invalid-staging-url", "Staging URL must not resolve to a local-only host"))


def _validate_run_url(value: str, field: str, findings: list[Finding]) -> None:
    if not RUN_URL_RE.fullmatch(value):
        findings.append(
            Finding(
                "invalid-workflow-run-url",
                f"{field} must be an immutable GitHub Actions run URL",
            )
        )


def validate_record(text: str) -> list[Finding]:
    lines = text.splitlines()
    fields = _field_map(lines)
    rows = _table_rows(lines)
    findings: list[Finding] = []

    sha = fields.get("Release candidate SHA", "")
    if not SHA_RE.fullmatch(sha):
        findings.append(
            Finding(
                "invalid-sha",
                "Release candidate SHA must be exactly 40 lowercase hexadecimal characters",
            )
        )

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

    _validate_run_url(
        fields.get("Staging deploy workflow run", ""),
        "Staging deploy workflow run",
        findings,
    )
    _validate_run_url(
        fields.get("Staging frontend deploy workflow run", ""),
        "Staging frontend deploy workflow run",
        findings,
    )
    _validate_staging_url(fields.get("Staging URL", ""), findings)

    acceptance_time = _parse_utc_timestamp(
        fields.get("Acceptance date/time (UTC)", ""),
        "Acceptance date/time (UTC)",
        findings,
    )
    decision_time = _parse_utc_timestamp(
        fields.get("Decision timestamp (UTC)", ""),
        "Decision timestamp (UTC)",
        findings,
    )
    if acceptance_time and decision_time and decision_time < acceptance_time:
        findings.append(
            Finding(
                "invalid-timestamp-order",
                "Decision timestamp must be at or after the acceptance timestamp",
            )
        )

    for field in (
        "Acceptance owner",
        "Previous deployable image SHA",
        "Database migration revision before deploy",
        "Database migration revision after deploy",
    ):
        if not fields.get(field):
            findings.append(Finding("missing-field", f"Required field is blank: {field}"))

    previous_sha = fields.get("Previous deployable image SHA", "")
    if previous_sha and not SHA_RE.fullmatch(previous_sha):
        findings.append(
            Finding(
                "invalid-previous-sha",
                "Previous deployable image SHA must be exactly 40 lowercase hexadecimal characters",
            )
        )
    if sha and previous_sha and sha == previous_sha:
        findings.append(
            Finding(
                "invalid-rollback-target",
                "Previous deployable image SHA must differ from the release candidate SHA",
            )
        )

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

    unresolved_critical = fields.get("Unresolved critical defects", "")
    unresolved_high = fields.get("Unresolved high-severity defects", "")
    if decision == "GO":
        allowed_zero = {"0", "None", "none"}
        if unresolved_critical not in allowed_zero:
            findings.append(Finding("blocking-defect", "GO requires zero unresolved critical defects"))
        if unresolved_high not in allowed_zero:
            findings.append(Finding("blocking-defect", "GO requires zero unresolved high-severity defects"))
        if "exact release candidate SHA and backend and frontend image digests" not in text:
            findings.append(
                Finding(
                    "missing-signoff",
                    "GO requires the full image-provenance sign-off statement",
                )
            )

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
