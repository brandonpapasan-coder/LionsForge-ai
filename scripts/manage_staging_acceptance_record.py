from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "lionsforge.staging-acceptance-record"
RECEIPT_SCHEMA = "lionsforge.staging-acceptance-record-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
REQUIRED_EVIDENCE = (
    "backend_deployment",
    "backup_restore",
    "candidate_manifest",
    "frontend_deployment",
    "https_api_smoke",
    "https_web_smoke",
    "observability",
    "rollback",
    "staging_preflight",
    "staging_preflight_upload_receipt",
)
_SHA = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
_URL = re.compile(r"https://[^\s]+")
_PRIVATE = re.compile(
    r"(?:secret|token|password|api[_-]?key|private[_-]?data|request[_-]?content)",
    re.IGNORECASE,
)
NOTICE = (
    "This record summarizes supplied staging acceptance evidence only. It does not provision infrastructure, "
    "perform deployment, independently execute live checks, or authorize production, beta, legal, or general availability."
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
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    return parsed.astimezone(timezone.utc)


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
    required = {"candidate_sha", "selection_rationale", "generated_at", "evidence"}
    findings = [f"unexpected generation input field: {key}" for key in sorted(set(value) - required)]
    findings += [f"missing generation input field: {key}" for key in sorted(required - set(value))]
    sha = value.get("candidate_sha")
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        findings.append("candidate_sha must be a lowercase 40-character commit SHA")
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
    if not isinstance(value.get("evidence"), list):
        findings.append("evidence must be an array")
    findings.extend(_scan(value))
    return sorted(set(findings))


def _evidence_structural_findings(evidence: Any, candidate_sha: str | None) -> tuple[list[str], bool]:
    findings: list[str] = []
    eligible = True
    if not isinstance(evidence, list) or len(evidence) != len(REQUIRED_EVIDENCE):
        return ["evidence must contain exactly the required acceptance categories"], False
    if evidence != sorted(evidence, key=lambda item: item.get("category", "") if isinstance(item, dict) else ""):
        findings.append("evidence ordering is not deterministic")
    names = [item.get("category") for item in evidence if isinstance(item, dict)]
    if tuple(names) != REQUIRED_EVIDENCE or len(set(names)) != len(names):
        findings.append("evidence categories are missing, duplicated, extra, or out of order")
    expected = {
        "category",
        "candidate_sha",
        "artifact_id",
        "artifact_url",
        "artifact_digest",
        "verified",
        "status",
        "observed_at",
        "summary",
    }
    for item in evidence:
        if not isinstance(item, dict) or set(item) != expected:
            findings.append("evidence fields are invalid")
            eligible = False
            continue
        if not isinstance(item["artifact_id"], int) or item["artifact_id"] <= 0:
            findings.append(f"evidence {item['category']} artifact_id must be a positive integer")
        if not isinstance(item["artifact_url"], str) or not _URL.fullmatch(item["artifact_url"]):
            findings.append(f"evidence {item['category']} artifact_url must be HTTPS")
        if not isinstance(item["artifact_digest"], str) or not _SHA256.fullmatch(item["artifact_digest"]):
            findings.append(f"evidence {item['category']} artifact_digest must be sha256-prefixed lowercase hex")
        if not isinstance(item["candidate_sha"], str) or not _SHA.fullmatch(item["candidate_sha"]):
            findings.append(f"evidence {item['category']} candidate_sha is invalid")
        elif candidate_sha and item["candidate_sha"] != candidate_sha:
            eligible = False
        if not isinstance(item["verified"], bool):
            findings.append(f"evidence {item['category']} verified must be boolean")
        elif item["verified"] is not True:
            eligible = False
        if item["status"] not in {"passed", "failed", "incomplete"}:
            findings.append(f"evidence {item['category']} status is invalid")
        elif item["status"] != "passed":
            eligible = False
        if not isinstance(item["summary"], str) or not item["summary"].strip() or len(item["summary"]) > 500:
            findings.append(f"evidence {item['category']} summary must contain 1 to 500 characters")
        try:
            parse_utc(item["observed_at"])
        except (KeyError, TypeError, ValueError):
            findings.append(f"evidence {item.get('category', 'unknown')} observed_at is invalid")
    return sorted(set(findings)), eligible


def build_record(
    *,
    candidate_sha: str,
    selection_rationale: str,
    evidence: list[dict[str, Any]],
    generated_at: datetime,
) -> dict[str, Any]:
    ordered = sorted(evidence, key=lambda item: item.get("category", ""))
    structural, eligible = _evidence_structural_findings(ordered, candidate_sha)
    record = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "candidate_sha": candidate_sha,
        "candidate_ref": "refs/heads/main",
        "selection_rationale": selection_rationale.strip(),
        "generated_at": utc_z(generated_at),
        "required_evidence": list(REQUIRED_EVIDENCE),
        "evidence": ordered,
        "decision": "GO" if eligible and not structural else "NO-GO",
        "interpretation_notice": NOTICE,
    }
    findings = validate_record(record)
    if findings:
        raise ValueError("Invalid staging acceptance record: " + "; ".join(findings))
    return record


def validate_record(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["record must be an object"]
    required = {
        "schema",
        "schema_version",
        "generator_version",
        "candidate_sha",
        "candidate_ref",
        "selection_rationale",
        "generated_at",
        "required_evidence",
        "evidence",
        "decision",
        "interpretation_notice",
    }
    findings = [f"unexpected record field: {key}" for key in sorted(set(value) - required)]
    findings += [f"missing record field: {key}" for key in sorted(required - set(value))]
    sha = value.get("candidate_sha")
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        findings.append("candidate_sha must be a lowercase 40-character commit SHA")
    if value.get("schema") != SCHEMA or value.get("schema_version") != SCHEMA_VERSION:
        findings.append("unsupported record schema or version")
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
    if value.get("required_evidence") != list(REQUIRED_EVIDENCE):
        findings.append("required evidence set or ordering mismatch")
    structural, eligible = _evidence_structural_findings(value.get("evidence"), sha if isinstance(sha, str) else None)
    findings.extend(structural)
    expected_decision = "GO" if eligible and not structural else "NO-GO"
    if value.get("decision") != expected_decision:
        findings.append("record decision mismatch")
    if value.get("interpretation_notice") != NOTICE:
        findings.append("interpretation notice mismatch")
    findings.extend(_scan(value))
    return sorted(set(findings))


def build_receipt(record: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_record(record)
    if findings:
        raise ValueError("Cannot receipt invalid record: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "record_sha256": digest(record),
        "candidate_sha": record["candidate_sha"],
        "decision": record["decision"],
        "generated_at": utc_z(generated_at),
    }


def validate_bundle(value: Any) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"record", "receipt"}:
        return ["bundle fields are invalid"]
    record, receipt = value["record"], value["receipt"]
    findings = validate_record(record)
    if not isinstance(receipt, dict):
        return sorted(set(findings + ["receipt must be an object"]))
    required = {
        "schema",
        "schema_version",
        "generator_version",
        "record_sha256",
        "candidate_sha",
        "decision",
        "generated_at",
    }
    findings += [f"unexpected receipt field: {key}" for key in sorted(set(receipt) - required)]
    findings += [f"missing receipt field: {key}" for key in sorted(required - set(receipt))]
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("unsupported receipt schema")
    if isinstance(record, dict):
        if receipt.get("record_sha256") != digest(record):
            findings.append("record digest mismatch")
        if receipt.get("candidate_sha") != record.get("candidate_sha"):
            findings.append("candidate SHA mismatch")
        if receipt.get("decision") != record.get("decision"):
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
    record = build_record(
        candidate_sha=input_payload["candidate_sha"],
        selection_rationale=input_payload["selection_rationale"],
        evidence=input_payload["evidence"],
        generated_at=generated_at,
    )
    return {"record": record, "receipt": build_receipt(record, generated_at=generated_at)}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("input", type=Path)
    generate.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("bundle", type=Path)
    args = parser.parse_args()
    if args.command == "generate":
        bundle = generate_bundle(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"decision": bundle["record"]["decision"], "output": str(args.output)}, sort_keys=True))
        return 0 if bundle["record"]["decision"] == "GO" else 2
    payload = json.loads(args.bundle.read_text(encoding="utf-8"))
    findings = validate_bundle(payload)
    print(json.dumps({"valid": not findings, "findings": findings}, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
