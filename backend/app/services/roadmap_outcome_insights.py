from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from statistics import median
from typing import Any

INSIGHT_SCHEMA = "lionsforge.roadmap-outcome-insights"
RECEIPT_SCHEMA = "lionsforge.roadmap-outcome-insights-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
MIN_GROUP_SIZE = 3
MAX_GROUPS = 100
ADVISORY_NOTICE = (
    "These insights describe workflow progression only. They are not proof of learning effectiveness, causation, "
    "accreditation, licensing, degree equivalence, professional certification, employment qualification or verification, "
    "individualized financial advice, autonomous competency approval, ranking, or prediction."
)

_DIGEST = re.compile(r"[0-9a-f]{64}")
_PRIVATE_FIELDS = re.compile(
    r"(?:project[_-]?title|research[_-]?content|evidence[_-]?(?:summary|title)|reflection|prompt|"
    r"reviewer[_-]?notes|answer[_-]?key|private[_-]?content|credential)",
    re.IGNORECASE,
)
_ALLOWED_STATUSES = ("not_started", "in_progress", "review_ready", "completed")


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _utc_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _duration_hours(acted_at: str, completed_at: str) -> float:
    acted = datetime.fromisoformat(acted_at.removesuffix("Z") + "+00:00")
    completed = datetime.fromisoformat(completed_at.removesuffix("Z") + "+00:00")
    return round((completed - acted).total_seconds() / 3600, 2)


def _group(entries: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        values = entry[key] if isinstance(entry[key], list) else [entry[key]]
        for value in values:
            grouped.setdefault(value, []).append(entry)
    rows: list[dict[str, Any]] = []
    for value, items in grouped.items():
        completed = [item for item in items if item["outcome_status"] == "completed"]
        durations = [_duration_hours(item["acted_at"], item["completed_at"]) for item in completed]
        row = {
            "group_key": value,
            "action_count": len(items),
            "completed_count": len(completed),
            "completed_rate": None,
            "median_completion_hours": None,
            "statistics_suppressed": len(items) < MIN_GROUP_SIZE,
        }
        if len(items) >= MIN_GROUP_SIZE:
            row["completed_rate"] = round(len(completed) / len(items), 4)
            if durations:
                row["median_completion_hours"] = round(float(median(durations)), 2)
        rows.append(row)
    return sorted(rows, key=lambda row: (-row["action_count"], row["group_key"]))[:MAX_GROUPS]


def build_insights(*, source_report: dict[str, Any], generated_at: datetime) -> dict[str, Any]:
    entries = source_report["entries"]
    status_counts = {status: sum(1 for entry in entries if entry["outcome_status"] == status) for status in _ALLOWED_STATUSES}
    completed = [entry for entry in entries if entry["outcome_status"] == "completed"]
    durations = [_duration_hours(entry["acted_at"], entry["completed_at"]) for entry in completed]
    insights = {
        "schema": INSIGHT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "learner_user_id": source_report["learner_user_id"],
        "generated_at": _utc_z(generated_at),
        "source_report_sha256": sha256_digest(source_report),
        "source_excluded_record_count": source_report["excluded_record_count"],
        "total_action_count": len(entries),
        "status_counts": status_counts,
        "completed_rate": round(len(completed) / len(entries), 4) if entries else None,
        "median_completion_hours": round(float(median(durations)), 2) if durations else None,
        "by_template": _group(entries, "template_slug"),
        "by_recommendation_reason": _group(entries, "recommendation_reason_codes"),
        "minimum_group_size": MIN_GROUP_SIZE,
        "advisory_notice": ADVISORY_NOTICE,
    }
    findings = validate_insights(insights)
    if findings:
        raise ValueError("Invalid roadmap outcome insights: " + "; ".join(findings))
    return insights


def validate_insights(insights: Any) -> list[str]:
    if not isinstance(insights, dict):
        return ["insights must be an object"]
    findings: list[str] = []
    required = {
        "schema", "schema_version", "generator_version", "learner_user_id", "generated_at",
        "source_report_sha256", "source_excluded_record_count", "total_action_count", "status_counts",
        "completed_rate", "median_completion_hours", "by_template", "by_recommendation_reason",
        "minimum_group_size", "advisory_notice",
    }
    findings.extend(f"unexpected insight field: {field}" for field in sorted(set(insights) - required))
    findings.extend(f"missing insight field: {field}" for field in sorted(required - set(insights)))
    if insights.get("schema") != INSIGHT_SCHEMA:
        findings.append("unsupported insight schema")
    if insights.get("schema_version") != SCHEMA_VERSION or insights.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported insight version")
    if insights.get("advisory_notice") != ADVISORY_NOTICE:
        findings.append("insight advisory notice mismatch")
    if not isinstance(insights.get("learner_user_id"), int) or insights.get("learner_user_id", 0) <= 0:
        findings.append("learner_user_id must be a positive integer")
    if not isinstance(insights.get("source_report_sha256"), str) or not _DIGEST.fullmatch(insights["source_report_sha256"]):
        findings.append("source_report_sha256 must be a lowercase SHA-256 digest")
    counts = insights.get("status_counts")
    if not isinstance(counts, dict) or tuple(counts) != _ALLOWED_STATUSES or any(not isinstance(value, int) or value < 0 for value in counts.values()):
        findings.append("status_counts are invalid")
    elif sum(counts.values()) != insights.get("total_action_count"):
        findings.append("status counts do not match total action count")
    for name in ("by_template", "by_recommendation_reason"):
        rows = insights.get(name)
        if not isinstance(rows, list) or len(rows) > MAX_GROUPS:
            findings.append(f"{name} must be a bounded list")
            continue
        if rows != sorted(rows, key=lambda row: (-row.get("action_count", 0), row.get("group_key", ""))):
            findings.append(f"{name} ordering is not deterministic")
        for row in rows:
            if set(row) != {"group_key", "action_count", "completed_count", "completed_rate", "median_completion_hours", "statistics_suppressed"}:
                findings.append(f"{name} row fields are invalid")
                continue
            suppressed = row["action_count"] < MIN_GROUP_SIZE
            if row["statistics_suppressed"] != suppressed:
                findings.append(f"{name} suppression mismatch")
            if suppressed and (row["completed_rate"] is not None or row["median_completion_hours"] is not None):
                findings.append(f"{name} suppressed statistics must be null")
    findings.extend(_scan_private_fields(insights))
    return sorted(set(findings))


def build_receipt(insights: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_insights(insights)
    if findings:
        raise ValueError("Cannot receipt invalid roadmap outcome insights: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "insights_sha256": sha256_digest(insights),
        "source_report_sha256": insights["source_report_sha256"],
        "total_action_count": insights["total_action_count"],
        "generated_at": _utc_z(generated_at),
    }


def validate_receipt(receipt: Any, insights: Any) -> list[str]:
    findings = validate_insights(insights)
    if not isinstance(receipt, dict):
        return sorted(set(findings + ["receipt must be an object"]))
    required = {"schema", "schema_version", "generator_version", "insights_sha256", "source_report_sha256", "total_action_count", "generated_at"}
    findings.extend(f"unexpected receipt field: {field}" for field in sorted(set(receipt) - required))
    findings.extend(f"missing receipt field: {field}" for field in sorted(required - set(receipt)))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("unsupported receipt schema")
    if isinstance(insights, dict):
        if receipt.get("insights_sha256") != sha256_digest(insights):
            findings.append("insights digest mismatch")
        if receipt.get("source_report_sha256") != insights.get("source_report_sha256"):
            findings.append("source report digest mismatch")
        if receipt.get("total_action_count") != insights.get("total_action_count"):
            findings.append("total action count mismatch")
    findings.extend(_scan_private_fields(receipt))
    return sorted(set(findings))
