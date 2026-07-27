from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

REPORT_SCHEMA = "lionsforge.roadmap-action-outcome-report"
RECEIPT_SCHEMA = "lionsforge.roadmap-action-outcome-report-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
MAX_ENTRIES = 200
MAX_EXCLUDED_FINDINGS = 25
ADVISORY_NOTICE = (
    "This report measures workflow progression after explicit learner roadmap actions. "
    "It is not accreditation, licensing, degree equivalence, professional certification, employment "
    "verification, individualized financial advice, autonomous competency approval, or proof that learning "
    "caused an external outcome."
)

_DIGEST = re.compile(r"[0-9a-f]{64}")
_PRIVATE_FIELDS = re.compile(
    r"(?:project[_-]?title|research[_-]?content|evidence[_-]?(?:summary|title)|reflection|prompt|"
    r"reviewer[_-]?notes|answer[_-]?key|private[_-]?content|credential)",
    re.IGNORECASE,
)
_ALLOWED_STATUSES = {"not_started", "in_progress", "review_ready", "completed"}
_ALLOWED_REASONS = {
    "adds_not_yet_demonstrated_competency",
    "strengthens_developing_competency",
}
_ENTRY_FIELDS = {
    "learner_user_id",
    "enrollment_id",
    "outcome_status",
    "template_slug",
    "template_version",
    "research_project_id",
    "recommendation_reason_codes",
    "action_sha256",
    "action_receipt_sha256",
    "acted_at",
    "completed_at",
    "completion_record_sha256",
}
_REPORT_FIELDS = {
    "schema",
    "schema_version",
    "generator_version",
    "learner_user_id",
    "generated_at",
    "entries",
    "excluded_record_count",
    "excluded_findings",
    "advisory_notice",
}
_RECEIPT_FIELDS = {
    "schema",
    "schema_version",
    "generator_version",
    "report_sha256",
    "entry_count",
    "completed_entry_count",
    "excluded_record_count",
    "generated_at",
}


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _utc_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _valid_timestamp(value: Any, *, nullable: bool = False) -> bool:
    if value is None:
        return nullable
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
            if _PRIVATE_FIELDS.search(str(key)):
                findings.append(f"prohibited private-content field at {child_path}")
            findings.extend(_scan_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_scan_private_fields(child, f"{path}[{index}]"))
    return findings


def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, int]:
    return (str(entry["acted_at"]), int(entry["enrollment_id"]))


def validate_entry(entry: Any, *, learner_user_id: int | None = None) -> list[str]:
    if not isinstance(entry, dict):
        return ["outcome entry must be an object"]
    findings: list[str] = []
    findings.extend(f"unexpected outcome entry field: {field}" for field in sorted(set(entry) - _ENTRY_FIELDS))
    findings.extend(f"missing outcome entry field: {field}" for field in sorted(_ENTRY_FIELDS - set(entry)))
    for field in ("learner_user_id", "enrollment_id", "template_version", "research_project_id"):
        if not isinstance(entry.get(field), int) or entry.get(field, 0) <= 0:
            findings.append(f"{field} must be a positive integer")
    if learner_user_id is not None and entry.get("learner_user_id") != learner_user_id:
        findings.append("outcome entry learner binding mismatch")
    status = entry.get("outcome_status")
    if status not in _ALLOWED_STATUSES:
        findings.append("unsupported outcome status")
    if not isinstance(entry.get("template_slug"), str) or not entry.get("template_slug", "").strip():
        findings.append("template_slug must be non-empty")
    reasons = entry.get("recommendation_reason_codes")
    if not isinstance(reasons, list) or not reasons or reasons != sorted(set(reasons)) or not set(reasons).issubset(_ALLOWED_REASONS):
        findings.append("recommendation reason codes are invalid")
    for field in ("action_sha256", "action_receipt_sha256"):
        if not isinstance(entry.get(field), str) or not _DIGEST.fullmatch(entry[field]):
            findings.append(f"{field} must be a lowercase SHA-256 digest")
    if not _valid_timestamp(entry.get("acted_at")):
        findings.append("acted_at must be a UTC Z timestamp")
    completed_at = entry.get("completed_at")
    completion_digest = entry.get("completion_record_sha256")
    if status == "completed":
        if not _valid_timestamp(completed_at):
            findings.append("completed outcome requires completed_at")
        if not isinstance(completion_digest, str) or not _DIGEST.fullmatch(completion_digest):
            findings.append("completed outcome requires completion_record_sha256")
    elif completed_at is not None or completion_digest is not None:
        findings.append("non-completed outcome must not include completion provenance")
    findings.extend(_scan_private_fields(entry))
    return sorted(set(findings))


def build_report(
    *,
    learner_user_id: int,
    generated_at: datetime,
    entries: list[dict[str, Any]],
    excluded_record_count: int = 0,
    excluded_findings: list[str] | None = None,
) -> dict[str, Any]:
    normalized = [{**entry, "recommendation_reason_codes": sorted(set(entry["recommendation_reason_codes"]))} for entry in entries]
    normalized.sort(key=_entry_sort_key, reverse=True)
    report = {
        "schema": REPORT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "learner_user_id": learner_user_id,
        "generated_at": _utc_z(generated_at),
        "entries": normalized[:MAX_ENTRIES],
        "excluded_record_count": excluded_record_count,
        "excluded_findings": sorted(set(excluded_findings or []))[:MAX_EXCLUDED_FINDINGS],
        "advisory_notice": ADVISORY_NOTICE,
    }
    findings = validate_report(report)
    if findings:
        raise ValueError("Invalid roadmap action outcome report: " + "; ".join(findings))
    return report


def validate_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["report must be an object"]
    findings: list[str] = []
    findings.extend(f"unexpected report field: {field}" for field in sorted(set(report) - _REPORT_FIELDS))
    findings.extend(f"missing report field: {field}" for field in sorted(_REPORT_FIELDS - set(report)))
    if report.get("schema") != REPORT_SCHEMA:
        findings.append("unsupported report schema")
    if report.get("schema_version") != SCHEMA_VERSION:
        findings.append("unsupported report schema version")
    if report.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported report generator version")
    if report.get("advisory_notice") != ADVISORY_NOTICE:
        findings.append("report advisory notice mismatch")
    learner_user_id = report.get("learner_user_id")
    if not isinstance(learner_user_id, int) or learner_user_id <= 0:
        findings.append("learner_user_id must be a positive integer")
    if not _valid_timestamp(report.get("generated_at")):
        findings.append("generated_at must be a UTC Z timestamp")
    entries = report.get("entries")
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        findings.append("entries must be a bounded list")
    else:
        expected = sorted(entries, key=_entry_sort_key, reverse=True) if all(isinstance(item, dict) for item in entries) else []
        if entries != expected:
            findings.append("entries must use deterministic reverse-chronological ordering")
        enrollment_ids: list[Any] = []
        for entry in entries:
            findings.extend(validate_entry(entry, learner_user_id=learner_user_id))
            if isinstance(entry, dict):
                enrollment_ids.append(entry.get("enrollment_id"))
        if len(enrollment_ids) != len(set(enrollment_ids)):
            findings.append("duplicate enrollment_id in report")
    if not isinstance(report.get("excluded_record_count"), int) or report.get("excluded_record_count", -1) < 0:
        findings.append("excluded_record_count must be a non-negative integer")
    excluded = report.get("excluded_findings")
    if not isinstance(excluded, list) or len(excluded) > MAX_EXCLUDED_FINDINGS:
        findings.append("excluded_findings must be a bounded list")
    elif excluded != sorted(set(excluded)) or not all(isinstance(item, str) and item for item in excluded):
        findings.append("excluded_findings must be unique sorted non-empty strings")
    findings.extend(_scan_private_fields(report))
    return sorted(set(findings))


def build_receipt(report: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_report(report)
    if findings:
        raise ValueError("Cannot receipt invalid roadmap action outcome report: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "report_sha256": sha256_digest(report),
        "entry_count": len(report["entries"]),
        "completed_entry_count": sum(1 for entry in report["entries"] if entry["outcome_status"] == "completed"),
        "excluded_record_count": report["excluded_record_count"],
        "generated_at": _utc_z(generated_at),
    }


def validate_receipt(receipt: Any, report: Any) -> list[str]:
    findings = validate_report(report)
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
        findings.append("receipt generated_at must be a UTC Z timestamp")
    if isinstance(report, dict):
        entries = report.get("entries", [])
        if receipt.get("report_sha256") != sha256_digest(report):
            findings.append("report digest mismatch")
        if receipt.get("entry_count") != len(entries):
            findings.append("report entry count mismatch")
        if receipt.get("completed_entry_count") != sum(1 for entry in entries if isinstance(entry, dict) and entry.get("outcome_status") == "completed"):
            findings.append("completed entry count mismatch")
        if receipt.get("excluded_record_count") != report.get("excluded_record_count"):
            findings.append("excluded record count mismatch")
    findings.extend(_scan_private_fields(receipt))
    return sorted(set(findings))
