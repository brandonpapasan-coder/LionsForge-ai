from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "lionsforge.staging-candidate-manifest"
RECEIPT_SCHEMA = "lionsforge.staging-candidate-manifest-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
REQUIRED_WORKFLOWS = (
    "Backend CI",
    "Deployment Validation",
    "Frontend CI",
    "Internal Alpha Upload Receipt CI",
    "Security Gate",
)
_SHA = re.compile(r"[0-9a-f]{40}")
_PRIVATE = re.compile(r"(?:secret|token|password|api[_-]?key|private[_-]?data|request[_-]?content)", re.IGNORECASE)
NOTICE = (
    "This manifest proves repository candidate consistency only. It does not prove staging infrastructure, endpoint, "
    "deployment, rollback, backup/restore, observability, production, legal, beta, or general-availability acceptance."
)


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def utc_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _scan(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if _PRIVATE.search(str(key)):
                findings.append(f"prohibited sensitive field at {path}.{key}")
            findings.extend(_scan(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_scan(child, f"{path}[{index}]"))
    return findings


def build_manifest(*, candidate_sha: str, selection_rationale: str, ancestry_verified: bool,
                   workflows: list[dict[str, Any]], generated_at: datetime) -> dict[str, Any]:
    ordered = sorted(workflows, key=lambda item: item.get("name", ""))
    manifest = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "candidate_sha": candidate_sha,
        "candidate_ref": "refs/heads/main",
        "selection_rationale": selection_rationale.strip(),
        "protected_main_ancestry_verified": ancestry_verified,
        "generated_at": utc_z(generated_at),
        "required_workflows": list(REQUIRED_WORKFLOWS),
        "workflow_runs": ordered,
        "decision": "GO" if ancestry_verified and all(
            run.get("status") == "completed" and run.get("conclusion") == "success" and run.get("head_sha") == candidate_sha
            for run in ordered
        ) and tuple(run.get("name") for run in ordered) == REQUIRED_WORKFLOWS else "NO-GO",
        "interpretation_notice": NOTICE,
    }
    findings = validate_manifest(manifest)
    if findings:
        raise ValueError("Invalid staging candidate manifest: " + "; ".join(findings))
    return manifest


def validate_manifest(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["manifest must be an object"]
    required = {
        "schema", "schema_version", "generator_version", "candidate_sha", "candidate_ref",
        "selection_rationale", "protected_main_ancestry_verified", "generated_at", "required_workflows",
        "workflow_runs", "decision", "interpretation_notice",
    }
    findings = [f"unexpected manifest field: {key}" for key in sorted(set(value) - required)]
    findings += [f"missing manifest field: {key}" for key in sorted(required - set(value))]
    sha = value.get("candidate_sha")
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        findings.append("candidate_sha must be a lowercase 40-character commit SHA")
    if value.get("schema") != SCHEMA or value.get("schema_version") != SCHEMA_VERSION or value.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported manifest schema or version")
    if value.get("candidate_ref") != "refs/heads/main":
        findings.append("candidate_ref must be refs/heads/main")
    rationale = value.get("selection_rationale")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 500:
        findings.append("selection_rationale must contain 1 to 500 characters")
    if value.get("required_workflows") != list(REQUIRED_WORKFLOWS):
        findings.append("required workflow set or ordering mismatch")
    runs = value.get("workflow_runs")
    eligible = True
    if not isinstance(runs, list) or len(runs) != len(REQUIRED_WORKFLOWS):
        findings.append("workflow_runs must contain exactly the five authoritative workflows")
        eligible = False
    else:
        if runs != sorted(runs, key=lambda item: item.get("name", "")):
            findings.append("workflow run ordering is not deterministic")
        names = [run.get("name") for run in runs if isinstance(run, dict)]
        if tuple(names) != REQUIRED_WORKFLOWS or len(set(names)) != len(names):
            findings.append("workflow names are missing, duplicated, extra, or out of order")
            eligible = False
        expected_fields = {"name", "run_id", "run_number", "status", "conclusion", "head_sha"}
        for run in runs:
            if not isinstance(run, dict) or set(run) != expected_fields:
                findings.append("workflow run fields are invalid")
                eligible = False
                continue
            if not isinstance(run["run_id"], int) or run["run_id"] <= 0 or not isinstance(run["run_number"], int) or run["run_number"] <= 0:
                findings.append("workflow run identifiers must be positive integers")
                eligible = False
            if run["status"] != "completed" or run["conclusion"] != "success":
                findings.append(f"workflow {run['name']} is not successful")
                eligible = False
            if run["head_sha"] != sha:
                findings.append(f"workflow {run['name']} head SHA mismatch")
                eligible = False
    ancestry = value.get("protected_main_ancestry_verified") is True
    expected_decision = "GO" if ancestry and eligible else "NO-GO"
    if value.get("decision") != expected_decision:
        findings.append("manifest decision mismatch")
    if value.get("interpretation_notice") != NOTICE:
        findings.append("interpretation notice mismatch")
    findings.extend(_scan(value))
    return sorted(set(findings))


def build_receipt(manifest: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_manifest(manifest)
    if findings:
        raise ValueError("Cannot receipt invalid manifest: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "manifest_sha256": digest(manifest),
        "candidate_sha": manifest["candidate_sha"],
        "decision": manifest["decision"],
        "generated_at": utc_z(generated_at),
    }


def validate_bundle(value: Any) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"manifest", "receipt"}:
        return ["bundle fields are invalid"]
    manifest, receipt = value["manifest"], value["receipt"]
    findings = validate_manifest(manifest)
    if not isinstance(receipt, dict):
        return sorted(set(findings + ["receipt must be an object"]))
    required = {"schema", "schema_version", "generator_version", "manifest_sha256", "candidate_sha", "decision", "generated_at"}
    findings += [f"unexpected receipt field: {key}" for key in sorted(set(receipt) - required)]
    findings += [f"missing receipt field: {key}" for key in sorted(required - set(receipt))]
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("unsupported receipt schema")
    if isinstance(manifest, dict):
        if receipt.get("manifest_sha256") != digest(manifest):
            findings.append("manifest digest mismatch")
        if receipt.get("candidate_sha") != manifest.get("candidate_sha"):
            findings.append("candidate SHA mismatch")
        if receipt.get("decision") != manifest.get("decision"):
            findings.append("decision mismatch")
    findings.extend(_scan(receipt))
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("bundle", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.bundle.read_text())
    findings = validate_bundle(payload)
    print(json.dumps({"valid": not findings, "findings": findings}, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
