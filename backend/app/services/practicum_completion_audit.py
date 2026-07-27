from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

RECORD_SCHEMA = "lionsforge.practicum-completion-record"
RECEIPT_SCHEMA = "lionsforge.practicum-completion-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
ADVISORY_NOTICE = (
    "This artifact is an audit record of a completed research practicum. "
    "It is not accreditation, licensing, degree equivalence, professional certification, "
    "or autonomous competency approval."
)

_RECORD_FIELDS = {
    "schema",
    "schema_version",
    "generator_version",
    "enrollment_id",
    "learner_user_id",
    "template_slug",
    "template_version",
    "research_project_id",
    "status",
    "completed_at",
    "objectives",
    "review_history",
    "advisory_notice",
}
_RECEIPT_FIELDS = {
    "schema",
    "schema_version",
    "generator_version",
    "record_sha256",
    "generated_at",
}
_PRIVATE_CONTENT_FIELDS = re.compile(
    r"(?:prompt|reflection|summary|answer[_-]?key|private[_-]?content)",
    re.IGNORECASE,
)


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _utc_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_record(
    *,
    enrollment_id: int,
    learner_user_id: int,
    template_slug: str,
    template_version: int,
    research_project_id: int,
    completed_at: datetime,
    objectives: list[dict[str, Any]],
    review_history: list[dict[str, Any]],
) -> dict[str, Any]:
    record = {
        "schema": RECORD_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "enrollment_id": enrollment_id,
        "learner_user_id": learner_user_id,
        "template_slug": template_slug,
        "template_version": template_version,
        "research_project_id": research_project_id,
        "status": "completed",
        "completed_at": _utc_z(completed_at),
        "objectives": sorted(
            [
                {
                    "objective_key": item["objective_key"],
                    "sequence": item["sequence"],
                    "status": item["status"],
                    "referenced_evidence_ids": sorted(set(item["referenced_evidence_ids"])),
                }
                for item in objectives
            ],
            key=lambda item: (item["sequence"], item["objective_key"]),
        ),
        "review_history": sorted(
            [
                {
                    "decision_id": item["decision_id"],
                    "reviewer_user_id": item["reviewer_user_id"],
                    "decision": item["decision"],
                    "created_at": _utc_z(item["created_at"]),
                    "decision_source": "human_reviewer",
                }
                for item in review_history
            ],
            key=lambda item: (item["created_at"], item["decision_id"]),
        ),
        "advisory_notice": ADVISORY_NOTICE,
    }
    findings = validate_record(record)
    if findings:
        raise ValueError("Invalid practicum completion record: " + "; ".join(findings))
    return record


def build_receipt(record: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_record(record)
    if findings:
        raise ValueError("Cannot receipt invalid practicum completion record: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "record_sha256": sha256_digest(record),
        "generated_at": _utc_z(generated_at),
    }


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return False
    return True


def _scan_private_fields(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _PRIVATE_CONTENT_FIELDS.search(str(key)):
                findings.append(f"prohibited private-content field at {child_path}")
            findings.extend(_scan_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_scan_private_fields(child, f"{path}[{index}]"))
    return findings


def validate_record(record: Any) -> list[str]:
    findings: list[str] = []
    if not isinstance(record, dict):
        return ["record must be an object"]
    findings.extend(f"unexpected record field: {field}" for field in sorted(set(record) - _RECORD_FIELDS))
    findings.extend(f"missing record field: {field}" for field in sorted(_RECORD_FIELDS - set(record)))
    if record.get("schema") != RECORD_SCHEMA:
        findings.append("unsupported record schema")
    if record.get("schema_version") != SCHEMA_VERSION:
        findings.append("unsupported record schema version")
    if record.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported record generator version")
    if record.get("status") != "completed":
        findings.append("record status must be completed")
    if record.get("advisory_notice") != ADVISORY_NOTICE:
        findings.append("record advisory notice mismatch")
    if not _valid_timestamp(record.get("completed_at")):
        findings.append("completed_at must be a UTC Z timestamp")

    objectives = record.get("objectives")
    if not isinstance(objectives, list) or not objectives:
        findings.append("objectives must be a non-empty list")
    else:
        expected = sorted(objectives, key=lambda item: (item.get("sequence", 0), item.get("objective_key", "")))
        if objectives != expected:
            findings.append("objectives must use deterministic sequence ordering")
        keys = [item.get("objective_key") for item in objectives if isinstance(item, dict)]
        if len(keys) != len(set(keys)):
            findings.append("duplicate objective_key")
        for item in objectives:
            if not isinstance(item, dict):
                findings.append("objective must be an object")
                continue
            if set(item) != {"objective_key", "sequence", "status", "referenced_evidence_ids"}:
                findings.append("objective fields are invalid")
            if item.get("status") != "approved":
                findings.append("completed record objectives must be approved")
            evidence_ids = item.get("referenced_evidence_ids")
            if not isinstance(evidence_ids, list) or evidence_ids != sorted(set(evidence_ids)):
                findings.append("evidence IDs must be unique and sorted")

    history = record.get("review_history")
    if not isinstance(history, list) or not history:
        findings.append("review_history must be a non-empty list")
    else:
        decision_ids = [item.get("decision_id") for item in history if isinstance(item, dict)]
        if len(decision_ids) != len(set(decision_ids)):
            findings.append("duplicate decision_id")
        for item in history:
            if not isinstance(item, dict):
                findings.append("review history item must be an object")
                continue
            if set(item) != {
                "decision_id",
                "reviewer_user_id",
                "decision",
                "created_at",
                "decision_source",
            }:
                findings.append("review history fields are invalid")
            if item.get("decision_source") != "human_reviewer":
                findings.append("review decision source must be human_reviewer")
            if item.get("decision") not in {"approved", "revision_required"}:
                findings.append("unsupported review decision")
            if not _valid_timestamp(item.get("created_at")):
                findings.append("review created_at must be a UTC Z timestamp")
        if isinstance(history[-1], dict) and history[-1].get("decision") != "approved":
            findings.append("final review decision must be approved")

    findings.extend(_scan_private_fields(record))
    return sorted(set(findings))


def validate_receipt(receipt: Any, record: Any) -> list[str]:
    findings = validate_record(record)
    if not isinstance(receipt, dict):
        return sorted(set(findings + ["receipt must be an object"]))
    findings.extend(f"unexpected receipt field: {field}" for field in sorted(set(receipt) - _RECEIPT_FIELDS))
    findings.extend(f"missing receipt field: {field}" for field in sorted(_RECEIPT_FIELDS - set(receipt)))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("unsupported receipt schema")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        findings.append("unsupported receipt schema version")
    if receipt.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported receipt generator version")
    if not _valid_timestamp(receipt.get("generated_at")):
        findings.append("generated_at must be a UTC Z timestamp")
    digest = receipt.get("record_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        findings.append("record_sha256 must be a lowercase SHA-256 digest")
    elif isinstance(record, dict) and digest != sha256_digest(record):
        findings.append("record digest mismatch")
    findings.extend(_scan_private_fields(receipt))
    return sorted(set(findings))
