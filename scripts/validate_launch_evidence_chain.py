#!/usr/bin/env python3
"""Validate the LionsForge AI launch evidence record chain.

This validator checks Markdown record structure and cross-record consistency only.
It does not verify live evidence or authorize deployment, beta, payments, public
registration, or general availability.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
FIELD_RE = re.compile(r"^- ([^:]+):\s*(.*)$")
CHECKBOX_DECISION_RE = re.compile(r"^- \[([ xX])\]\s+(GO|CONDITIONAL GO|NO-GO)\b")

VALIDATORS = {
    "production": ROOT / "scripts" / "validate_production_acceptance.py",
    "public_operations": ROOT / "scripts" / "validate_public_operations_activation.py",
    "controlled_beta": ROOT / "scripts" / "validate_controlled_beta_acceptance.py",
    "ga": ROOT / "scripts" / "validate_general_availability_decision.py",
}


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    record: str
    message: str


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"launch_chain_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _normalize(value: str) -> str:
    return value.strip().strip("`").strip()


def _fields(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = FIELD_RE.match(line.strip())
        if match:
            values[match.group(1).strip()] = _normalize(match.group(2))
    return values


def _decision(text: str, fields: dict[str, str]) -> str:
    direct = fields.get("Decision", "").upper()
    if direct in {"GO", "CONDITIONAL GO", "NO-GO"}:
        return direct
    selected: list[str] = []
    for line in text.splitlines():
        match = CHECKBOX_DECISION_RE.match(line.strip())
        if match and match.group(1).lower() == "x":
            selected.append(match.group(2))
    return selected[0] if len(selected) == 1 else ""


def _record_identity(kind: str, fields: dict[str, str]) -> tuple[str, str, str, str]:
    if kind == "public_operations":
        return fields.get("Release candidate SHA", ""), "", "", ""
    rollback_name = "Rollback SHA" if kind == "production" else "Previous rollback SHA"
    return (
        fields.get("Release SHA", ""),
        fields.get(rollback_name, ""),
        fields.get("Backend image digest", ""),
        fields.get("Frontend image digest", ""),
    )


def validate_chain(records: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    parsed: dict[str, dict[str, str]] = {}
    decisions: dict[str, str] = {}
    identities: dict[str, tuple[str, str, str, str]] = {}

    for kind in ("production", "public_operations", "controlled_beta", "ga"):
        text = records[kind]
        module = _load_module(kind, VALIDATORS[kind])
        for finding in module.validate_record(text):
            findings.append(
                Finding(
                    "record-invalid",
                    kind,
                    f"{getattr(finding, 'code', 'invalid')}: {getattr(finding, 'message', finding)}",
                )
            )
        parsed[kind] = _fields(text)
        decisions[kind] = _decision(text, parsed[kind])
        identities[kind] = _record_identity(kind, parsed[kind])

    prod_release, prod_rollback, prod_backend, prod_frontend = identities["production"]
    public_release, _, _, _ = identities["public_operations"]
    beta_release, beta_rollback, beta_backend, beta_frontend = identities["controlled_beta"]
    ga_release, ga_rollback, ga_backend, ga_frontend = identities["ga"]

    exact_pairs = (
        ("production release SHA", prod_release, ga_release),
        ("public-operations release SHA", public_release, ga_release),
        ("production rollback SHA", prod_rollback, ga_rollback),
        ("production backend image digest", prod_backend, ga_backend),
        ("production frontend image digest", prod_frontend, ga_frontend),
    )
    for label, upstream, ga_value in exact_pairs:
        if upstream and ga_value and upstream != ga_value:
            findings.append(Finding("identity-mismatch", "chain", f"{label} does not match GA"))

    ancestry = parsed["ga"].get("Candidate ancestry evidence", "")
    beta_exact = (
        beta_release == ga_release
        and beta_rollback == ga_rollback
        and beta_backend == ga_backend
        and beta_frontend == ga_frontend
    )
    if not beta_exact:
        if not ancestry:
            findings.append(
                Finding(
                    "missing-ancestry",
                    "ga",
                    "A differing controlled-beta candidate requires candidate ancestry evidence",
                )
            )
        if beta_release == ga_release:
            findings.append(
                Finding(
                    "ambiguous-lineage",
                    "chain",
                    "Matching beta and GA release SHAs cannot have differing rollback or image digests",
                )
            )

    evidence_fields = {
        "production": parsed["ga"].get("Production acceptance evidence", ""),
        "public_operations": parsed["ga"].get("Public-operations activation evidence", ""),
        "controlled_beta": parsed["ga"].get("Controlled-beta acceptance evidence", ""),
    }
    for name, value in evidence_fields.items():
        if not value:
            findings.append(Finding("missing-binding", "ga", f"Missing {name} evidence binding"))
    nonblank = [value for value in evidence_fields.values() if value]
    if len(nonblank) != len(set(nonblank)):
        findings.append(
            Finding("duplicate-binding", "ga", "Upstream evidence identifiers must be distinct")
        )

    if decisions["ga"] == "GO":
        for upstream in ("production", "public_operations", "controlled_beta"):
            if decisions[upstream] != "GO":
                findings.append(
                    Finding(
                        "decision-order",
                        upstream,
                        f"GA GO requires upstream decision GO, found {decisions[upstream] or 'unselected'}",
                    )
                )

    return sorted(set(findings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("production", type=Path)
    parser.add_argument("public_operations", type=Path)
    parser.add_argument("controlled_beta", type=Path)
    parser.add_argument("ga", type=Path)
    args = parser.parse_args(argv)

    records: dict[str, str] = {}
    for kind in ("production", "public_operations", "controlled_beta", "ga"):
        path = getattr(args, kind)
        try:
            records[kind] = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR record-unreadable [{kind}]: {exc}", file=sys.stderr)
            return 1

    findings = validate_chain(records)
    if findings:
        for finding in findings:
            print(f"ERROR {finding.code} [{finding.record}]: {finding.message}")
        print(f"INVALID: {len(findings)} finding(s)")
        return 1
    print("VALID: launch evidence chain is internally valid and cross-record consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
