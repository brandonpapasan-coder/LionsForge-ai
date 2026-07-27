from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Literal

TREND_SCHEMA = "lionsforge.roadmap-outcome-trends"
RECEIPT_SCHEMA = "lionsforge.roadmap-outcome-trends-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
MIN_WINDOW_SIZE = 3
MAX_WINDOWS = 366
SUPPORTED_GRANULARITIES = ("day", "week", "month")
ADVISORY_NOTICE = (
    "These trend snapshots describe workflow progression only. They are not proof of learning effectiveness, causation, "
    "accreditation, licensing, degree equivalence, professional certification, employment qualification or verification, "
    "individualized financial advice, autonomous competency approval, ranking, forecasting, or prediction."
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


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utc_z(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    return _utc(parsed)


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


def _duration_hours(entry: dict[str, Any]) -> float:
    acted = _parse_utc(entry["acted_at"])
    completed = _parse_utc(entry["completed_at"])
    if completed < acted:
        raise ValueError("completed_at cannot precede acted_at")
    return round((completed - acted).total_seconds() / 3600, 2)


def _floor_window(value: datetime, granularity: str) -> datetime:
    value = _utc(value)
    if granularity == "day":
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == "week":
        start = value - timedelta(days=value.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == "month":
        return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    raise ValueError("unsupported granularity")


def _next_window(value: datetime, granularity: str) -> datetime:
    if granularity == "day":
        return value + timedelta(days=1)
    if granularity == "week":
        return value + timedelta(days=7)
    if granularity == "month":
        return value.replace(year=value.year + 1, month=1) if value.month == 12 else value.replace(month=value.month + 1)
    raise ValueError("unsupported granularity")


def _window_row(start: datetime, end: datetime, entries: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = {status: sum(1 for entry in entries if entry["outcome_status"] == status) for status in _ALLOWED_STATUSES}
    completed = [entry for entry in entries if entry["outcome_status"] == "completed"]
    durations = [_duration_hours(entry) for entry in completed]
    suppressed = len(entries) < MIN_WINDOW_SIZE
    return {
        "window_start": _utc_z(start),
        "window_end": _utc_z(end),
        "action_count": len(entries),
        "status_counts": status_counts,
        "completed_count": len(completed),
        "completed_rate": None if suppressed else round(len(completed) / len(entries), 4),
        "median_completion_hours": None if suppressed or not durations else round(float(median(durations)), 2),
        "statistics_suppressed": suppressed,
    }


def build_trends(
    *,
    source_report: dict[str, Any],
    granularity: Literal["day", "week", "month"],
    range_start: datetime,
    range_end: datetime,
    generated_at: datetime,
) -> dict[str, Any]:
    if granularity not in SUPPORTED_GRANULARITIES:
        raise ValueError("unsupported granularity")
    start = _floor_window(range_start, granularity)
    end = _utc(range_end)
    if end <= start:
        raise ValueError("range_end must be after range_start")

    windows: list[dict[str, Any]] = []
    cursor = start
    entries = source_report["entries"]
    while cursor < end:
        if len(windows) >= MAX_WINDOWS:
            raise ValueError("trend window limit exceeded")
        next_cursor = min(_next_window(cursor, granularity), end)
        window_entries = [
            entry for entry in entries if cursor <= _parse_utc(entry["acted_at"]) < next_cursor
        ]
        windows.append(_window_row(cursor, next_cursor, window_entries))
        cursor = next_cursor

    trends = {
        "schema": TREND_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "learner_user_id": source_report["learner_user_id"],
        "generated_at": _utc_z(generated_at),
        "source_report_sha256": sha256_digest(source_report),
        "source_excluded_record_count": source_report["excluded_record_count"],
        "granularity": granularity,
        "range_start": _utc_z(start),
        "range_end": _utc_z(end),
        "minimum_window_size": MIN_WINDOW_SIZE,
        "windows": windows,
        "advisory_notice": ADVISORY_NOTICE,
    }
    findings = validate_trends(trends)
    if findings:
        raise ValueError("Invalid roadmap outcome trends: " + "; ".join(findings))
    return trends


def validate_trends(trends: Any) -> list[str]:
    if not isinstance(trends, dict):
        return ["trends must be an object"]
    required = {
        "schema", "schema_version", "generator_version", "learner_user_id", "generated_at",
        "source_report_sha256", "source_excluded_record_count", "granularity", "range_start",
        "range_end", "minimum_window_size", "windows", "advisory_notice",
    }
    findings = [f"unexpected trend field: {field}" for field in sorted(set(trends) - required)]
    findings.extend(f"missing trend field: {field}" for field in sorted(required - set(trends)))
    if trends.get("schema") != TREND_SCHEMA:
        findings.append("unsupported trend schema")
    if trends.get("schema_version") != SCHEMA_VERSION or trends.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported trend version")
    if trends.get("granularity") not in SUPPORTED_GRANULARITIES:
        findings.append("unsupported trend granularity")
    if trends.get("minimum_window_size") != MIN_WINDOW_SIZE:
        findings.append("minimum window size mismatch")
    if trends.get("advisory_notice") != ADVISORY_NOTICE:
        findings.append("trend advisory notice mismatch")
    if not isinstance(trends.get("source_report_sha256"), str) or not _DIGEST.fullmatch(trends["source_report_sha256"]):
        findings.append("source_report_sha256 must be a lowercase SHA-256 digest")

    windows = trends.get("windows")
    if not isinstance(windows, list) or len(windows) > MAX_WINDOWS:
        findings.append("windows must be a bounded list")
    else:
        previous_end: str | None = None
        for row in windows:
            expected = {"window_start", "window_end", "action_count", "status_counts", "completed_count", "completed_rate", "median_completion_hours", "statistics_suppressed"}
            if not isinstance(row, dict) or set(row) != expected:
                findings.append("window fields are invalid")
                continue
            if previous_end is not None and row["window_start"] != previous_end:
                findings.append("windows are overlapping or non-contiguous")
            previous_end = row["window_end"]
            counts = row["status_counts"]
            if not isinstance(counts, dict) or tuple(counts) != _ALLOWED_STATUSES:
                findings.append("window status counts are invalid")
                continue
            if sum(counts.values()) != row["action_count"]:
                findings.append("window status counts do not match action count")
            suppressed = row["action_count"] < MIN_WINDOW_SIZE
            if row["statistics_suppressed"] != suppressed:
                findings.append("window suppression mismatch")
            if suppressed and (row["completed_rate"] is not None or row["median_completion_hours"] is not None):
                findings.append("suppressed window statistics must be null")
    findings.extend(_scan_private_fields(trends))
    return sorted(set(findings))


def build_receipt(trends: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_trends(trends)
    if findings:
        raise ValueError("Cannot receipt invalid roadmap outcome trends: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "trends_sha256": sha256_digest(trends),
        "source_report_sha256": trends["source_report_sha256"],
        "window_count": len(trends["windows"]),
        "generated_at": _utc_z(generated_at),
    }


def validate_receipt(receipt: Any, trends: Any) -> list[str]:
    findings = validate_trends(trends)
    if not isinstance(receipt, dict):
        return sorted(set(findings + ["receipt must be an object"]))
    required = {"schema", "schema_version", "generator_version", "trends_sha256", "source_report_sha256", "window_count", "generated_at"}
    findings.extend(f"unexpected receipt field: {field}" for field in sorted(set(receipt) - required))
    findings.extend(f"missing receipt field: {field}" for field in sorted(required - set(receipt)))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("unsupported receipt schema")
    if isinstance(trends, dict):
        if receipt.get("trends_sha256") != sha256_digest(trends):
            findings.append("trends digest mismatch")
        if receipt.get("source_report_sha256") != trends.get("source_report_sha256"):
            findings.append("source report digest mismatch")
        if receipt.get("window_count") != len(trends.get("windows", [])):
            findings.append("window count mismatch")
    findings.extend(_scan_private_fields(receipt))
    return sorted(set(findings))
