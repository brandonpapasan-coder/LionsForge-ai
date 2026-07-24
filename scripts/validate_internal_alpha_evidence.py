#!/usr/bin/env python3
"""Require traceable evidence references for an Internal Alpha GO record."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DECISION_RE = re.compile(r"^- Decision:\s*\*\*(GO|NO-GO)\*\*\s*$", re.MULTILINE)
SHA_RE = re.compile(r"(?:^|[^0-9a-f])[0-9a-f]{40}(?:$|[^0-9a-f])")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
NUMBERED_REF_RE = re.compile(r"\b(?:PR|Issue|Run|Artifact)\s+#?\d+\b", re.IGNORECASE)
URL_RE = re.compile(r"https://[^\s`|]+")
REPO_PATH_RE = re.compile(r"(?:^|[\s`])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:$|[\s`])")
GENERIC_EVIDENCE = {
    "complete",
    "completed",
    "done",
    "evidence",
    "pass",
    "passed",
    "verified",
}


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


def _cells(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return []
    return [cell.strip().strip("`") for cell in stripped[1:-1].split("|")]


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(cell and set(cell) <= {"-", ":"} for cell in cells)


def _is_traceable(value: str) -> bool:
    normalized = value.strip().strip("`")
    if normalized.lower() in GENERIC_EVIDENCE:
        return False
    return any(
        pattern.search(normalized)
        for pattern in (URL_RE, SHA_RE, DIGEST_RE, NUMBERED_REF_RE, REPO_PATH_RE)
    )


def validate_evidence(text: str) -> list[Finding]:
    decision_match = DECISION_RE.search(text)
    if decision_match is None:
        return [Finding("invalid-decision", "Decision must be GO or NO-GO")]
    if decision_match.group(1) == "NO-GO":
        return []

    lines = text.splitlines()
    findings: list[Finding] = []
    index = 0
    while index < len(lines):
        header = _cells(lines[index])
        if not header or header[-1].lower() != "evidence":
            index += 1
            continue
        if index + 1 >= len(lines) or not _is_separator(_cells(lines[index + 1])):
            findings.append(
                Finding("malformed-evidence-table", "Evidence table is missing a separator row")
            )
            index += 1
            continue

        index += 2
        while index < len(lines):
            row = _cells(lines[index])
            if not row:
                break
            if len(row) != len(header):
                findings.append(
                    Finding(
                        "malformed-evidence-row",
                        f"Evidence row has the wrong column count: {row[0] if row else 'unknown'}",
                    )
                )
            else:
                evidence = row[-1]
                if not _is_traceable(evidence):
                    findings.append(
                        Finding(
                            "missing-evidence-reference",
                            f"GO control requires a traceable evidence reference: {row[0]}",
                        )
                    )
            index += 1
        continue

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

    findings = validate_evidence(text)
    if findings:
        for finding in findings:
            print(f"ERROR {finding.code}: {finding.message}")
        print(f"INVALID: {len(findings)} finding(s)")
        return 1

    print("VALID: Internal Alpha evidence references are traceable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
