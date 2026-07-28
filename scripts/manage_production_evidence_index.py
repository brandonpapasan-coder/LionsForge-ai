from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "lionsforge.production-evidence-index"
RECEIPT_SCHEMA = "lionsforge.production-evidence-index-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
REQUIRED_ENTRIES = (
    "accepted_staging_evidence_index",
    "ai_quota_cost_controls",
    "alert_verification",
    "backend_deployment",
    "backup_isolated_restore",
    "capacity_availability",
    "frontend_deployment",
    "https_api_smoke",
    "https_web_smoke",
    "least_privilege_security_review",
    "migration",
    "production_candidate_manifest",
    "production_preflight",
    "production_release_record",
    "required_workflow_evidence",
    "rollback",
)
_SHA = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_URL = re.compile(r"https://[^\s]+")
_PRIVATE = re.compile(
    r"(?:secret|token|password|api[_-]?key|private[_-]?data|request[_-]?content|kubeconfig|credential)",
    re.IGNORECASE,
)
NOTICE = (
    "This index binds supplied production evidence only. It does not provision infrastructure, perform deployment, "
    "independently execute live checks, or authorize public registration, controlled beta, legal readiness, or general availability."
)


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def utc_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp must end in Z")
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00").astimezone(timezone.utc)


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


def validate_generation_input(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["generation input must be an object"]
    required = {
        "candidate_sha",
        "staging_candidate_sha",
        "selection_rationale",
        "generated_at",
        "entries",
    }
    findings = [f"unexpected generation input field: {key}" for key in sorted(set(value) - required)]
    findings += [f"missing generation input field: {key}" for key in sorted(required - set(value))]
    for field in ("candidate_sha", "staging_candidate_sha"):
        sha = value.get(field)
        if not isinstance(sha, str) or not _SHA.fullmatch(sha):
            findings.append(f"{field} must be a lowercase 40-character commit SHA")
    rationale = value.get("selection_rationale")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 500:
        findings.append("selection_rationale must contain 1 to 500 characters")
    generated_at = value.get("generated_at")
    if not isinstance(generated_at, str):
        findings.append("generated_at must be a UTC timestamp string")
    else:
        try:
            parse_utc(generated_at)
        except (TypeError, ValueError):
            findings.append("generated_at must be a valid UTC timestamp ending in Z")
    if not isinstance(value.get("entries"), list):
        findings.append("entries must be an array")
    findings.extend(_scan(value))
    return sorted(set(findings))


def _entry_findings(
    entries: Any,
    candidate_sha: str | None,
    staging_candidate_sha: str | None,
) -> tuple[list[str], bool]:
    if not isinstance(entries, list) or len(entries) != len(REQUIRED_ENTRIES):
        return ["entries must contain exactly the required production evidence categories"], False
    findings: list[str] = []
    ready = True
    if entries != sorted(entries, key=lambda item: item.get("category", "") if isinstance(item, dict) else ""):
        findings.append("entry ordering is not deterministic")
    names = [item.get("category") for item in entries if isinstance(item, dict)]
    if tuple(names) != REQUIRED_ENTRIES or len(set(names)) != len(names):
        findings.append("entry categories are missing, duplicated, extra, or out of order")
    expected = {
        "category",
        "candidate_sha",
        "staging_candidate_sha",
        "artifact_id",
        "artifact_url",
        "artifact_digest",
        "workflow_run_id",
        "verified",
        "status",
        "decision",
        "observed_at",
        "summary",
    }
    for item in entries:
        if not isinstance(item, dict) or set(item) != expected:
            findings.append("entry fields are invalid")
            ready = False
            continue
        category = item["category"]
        if not isinstance(item["artifact_id"], int) or item["artifact_id"] <= 0:
            findings.append(f"entry {category} artifact_id must be a positive integer")
        if not isinstance(item["workflow_run_id"], int) or item["workflow_run_id"] <= 0:
            findings.append(f"entry {category} workflow_run_id must be a positive integer")
        if not isinstance(item["artifact_url"], str) or not _URL.fullmatch(item["artifact_url"]):
            findings.append(f"entry {category} artifact_url must be HTTPS")
        if not isinstance(item["artifact_digest"], str) or not _SHA256.fullmatch(item["artifact_digest"]):
            findings.append(f"entry {category} artifact_digest must be sha256-prefixed lowercase hex")
        entry_candidate = item["candidate_sha"]
        if not isinstance(entry_candidate, str) or not _SHA.fullmatch(entry_candidate):
            findings.append(f"entry {category} candidate_sha is invalid")
        elif candidate_sha and entry_candidate != candidate_sha:
            ready = False
        entry_staging = item["staging_candidate_sha"]
        if not isinstance(entry_staging, str) or not _SHA.fullmatch(entry_staging):
            findings.append(f"entry {category} staging_candidate_sha is invalid")
        elif staging_candidate_sha and entry_staging != staging_candidate_sha:
            ready = False
        if not isinstance(item["verified"], bool):
            findings.append(f"entry {category} verified must be boolean")
        elif item["verified"] is not True:
            ready = False
        if item["status"] not in {"passed", "failed", "incomplete"}:
            findings.append(f"entry {category} status is invalid")
        elif item["status"] != "passed":
            ready = False
        if item["decision"] not in {"GO", "NO-GO", "NOT-APPLICABLE"}:
            findings.append(f"entry {category} decision is invalid")
        elif category == "production_release_record":
            if item["decision"] != "GO":
                ready = False
        elif category == "accepted_staging_evidence_index":
            if item["decision"] != "GO":
                ready = False
        elif item["decision"] == "NO-GO":
            ready = False
        if not isinstance(item["summary"], str) or not item["summary"].strip() or len(item["summary"]) > 500:
            findings.append(f"entry {category} summary must contain 1 to 500 characters")
        try:
            parse_utc(item["observed_at"])
        except (KeyError, TypeError, ValueError):
            findings.append(f"entry {category} observed_at is invalid")
    return sorted(set(findings)), ready


def build_index(
    *,
    candidate_sha: str,
    staging_candidate_sha: str,
    selection_rationale: str,
    entries: list[dict[str, Any]],
    generated_at: datetime,
) -> dict[str, Any]:
    ordered = sorted((dict(item) for item in entries), key=lambda item: item.get("category", ""))
    structural, ready = _entry_findings(ordered, candidate_sha, staging_candidate_sha)
    index = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "candidate_sha": candidate_sha,
        "candidate_ref": "refs/heads/main",
        "staging_candidate_sha": staging_candidate_sha,
        "selection_rationale": selection_rationale.strip(),
        "generated_at": utc_z(generated_at),
        "required_entries": list(REQUIRED_ENTRIES),
        "entries": ordered,
        "decision": "READY" if ready and not structural else "NOT-READY",
        "interpretation_notice": NOTICE,
    }
    findings = validate_index(index)
    if findings:
        raise ValueError("Invalid production evidence index: " + "; ".join(findings))
    return index


def validate_index(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["index must be an object"]
    required = {
        "schema",
        "schema_version",
        "generator_version",
        "candidate_sha",
        "candidate_ref",
        "staging_candidate_sha",
        "selection_rationale",
        "generated_at",
        "required_entries",
        "entries",
        "decision",
        "interpretation_notice",
    }
    findings = [f"unexpected index field: {key}" for key in sorted(set(value) - required)]
    findings += [f"missing index field: {key}" for key in sorted(required - set(value))]
    candidate_sha = value.get("candidate_sha")
    staging_candidate_sha = value.get("staging_candidate_sha")
    for field, sha in (("candidate_sha", candidate_sha), ("staging_candidate_sha", staging_candidate_sha)):
        if not isinstance(sha, str) or not _SHA.fullmatch(sha):
            findings.append(f"{field} must be a lowercase 40-character commit SHA")
    if value.get("schema") != SCHEMA or value.get("schema_version") != SCHEMA_VERSION:
        findings.append("unsupported index schema or version")
    if value.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported generator version")
    if value.get("candidate_ref") != "refs/heads/main":
        findings.append("candidate_ref must be refs/heads/main")
    rationale = value.get("selection_rationale")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 500:
        findings.append("selection_rationale must contain 1 to 500 characters")
    try:
        parse_utc(value.get("generated_at"))
    except (TypeError, ValueError):
        findings.append("generated_at is invalid")
    if value.get("required_entries") != list(REQUIRED_ENTRIES):
        findings.append("required entry set or ordering mismatch")
    structural, ready = _entry_findings(
        value.get("entries"),
        candidate_sha if isinstance(candidate_sha, str) else None,
        staging_candidate_sha if isinstance(staging_candidate_sha, str) else None,
    )
    findings.extend(structural)
    expected_decision = "READY" if ready and not structural else "NOT-READY"
    if value.get("decision") != expected_decision:
        findings.append("index decision mismatch")
    if value.get("interpretation_notice") != NOTICE:
        findings.append("interpretation notice mismatch")
    findings.extend(_scan(value))
    return sorted(set(findings))


def build_receipt(index: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_index(index)
    if findings:
        raise ValueError("Cannot receipt invalid index: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "index_sha256": digest(index),
        "candidate_sha": index["candidate_sha"],
        "staging_candidate_sha": index["staging_candidate_sha"],
        "decision": index["decision"],
        "generated_at": utc_z(generated_at),
    }


def validate_bundle(value: Any) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"index", "receipt"}:
        return ["bundle fields are invalid"]
    index, receipt = value["index"], value["receipt"]
    findings = validate_index(index)
    if not isinstance(receipt, dict):
        return sorted(set(findings + ["receipt must be an object"]))
    required = {
        "schema",
        "schema_version",
        "generator_version",
        "index_sha256",
        "candidate_sha",
        "staging_candidate_sha",
        "decision",
        "generated_at",
    }
    findings += [f"unexpected receipt field: {key}" for key in sorted(set(receipt) - required)]
    findings += [f"missing receipt field: {key}" for key in sorted(required - set(receipt))]
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("unsupported receipt schema")
    if isinstance(index, dict):
        if receipt.get("index_sha256") != digest(index):
            findings.append("index digest mismatch")
        if receipt.get("candidate_sha") != index.get("candidate_sha"):
            findings.append("candidate SHA mismatch")
        if receipt.get("staging_candidate_sha") != index.get("staging_candidate_sha"):
            findings.append("staging candidate SHA mismatch")
        if receipt.get("decision") != index.get("decision"):
            findings.append("decision mismatch")
    try:
        parse_utc(receipt.get("generated_at"))
    except (TypeError, ValueError):
        findings.append("receipt generated_at is invalid")
    findings.extend(_scan(receipt))
    return sorted(set(findings))


def generate_bundle(input_payload: Any) -> dict[str, Any]:
    findings = validate_generation_input(input_payload)
    if findings:
        raise ValueError("Invalid generation input: " + "; ".join(findings))
    generated_at = parse_utc(input_payload["generated_at"])
    index = build_index(
        candidate_sha=input_payload["candidate_sha"],
        staging_candidate_sha=input_payload["staging_candidate_sha"],
        selection_rationale=input_payload["selection_rationale"],
        entries=input_payload["entries"],
        generated_at=generated_at,
    )
    return {"index": index, "receipt": build_receipt(index, generated_at=generated_at)}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("input", type=Path)
    generate.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            bundle = generate_bundle(json.loads(args.input.read_text(encoding="utf-8")))
            args.output.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({"decision": bundle["index"]["decision"], "output": str(args.output)}, sort_keys=True))
            return 0 if bundle["index"]["decision"] == "READY" else 2
        payload = json.loads(args.bundle.read_text(encoding="utf-8"))
        findings = validate_bundle(payload)
        print(json.dumps({"valid": not findings, "findings": findings}, sort_keys=True))
        return 0 if not findings else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
