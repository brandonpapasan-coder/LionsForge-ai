from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

PORTFOLIO_SCHEMA = "lionsforge.learner-competency-portfolio"
RECEIPT_SCHEMA = "lionsforge.learner-competency-portfolio-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
ADVISORY_NOTICE = (
    "This evidence-backed learning portfolio summarizes completed, human-approved research practica. "
    "It is not accreditation, licensing, degree equivalence, professional certification, employment "
    "verification, or autonomous competency approval."
)

_PORTFOLIO_FIELDS = {
    "schema",
    "schema_version",
    "generator_version",
    "learner_user_id",
    "generated_at",
    "competencies",
    "excluded_record_count",
    "advisory_notice",
}
_RECEIPT_FIELDS = {
    "schema",
    "schema_version",
    "generator_version",
    "portfolio_sha256",
    "generated_at",
}
_PRIVATE_FIELDS = re.compile(
    r"(?:prompt|reflection|summary|reviewer[_-]?notes|answer[_-]?key|private[_-]?content|credential)",
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


def build_portfolio(
    *,
    learner_user_id: int,
    generated_at: datetime,
    competency_rows: list[dict[str, Any]],
    excluded_record_count: int = 0,
) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in competency_rows:
        key = str(row["competency_key"])
        entry = grouped.setdefault(
            key,
            {
                "competency_key": key,
                "competency_label": str(row["competency_label"]),
                "practica": [],
            },
        )
        entry["practica"].append(
            {
                "enrollment_id": int(row["enrollment_id"]),
                "template_slug": str(row["template_slug"]),
                "template_version": int(row["template_version"]),
                "research_project_id": int(row["research_project_id"]),
                "completed_at": _utc_z(row["completed_at"]),
                "objective_keys": sorted(set(str(value) for value in row["objective_keys"])),
                "referenced_evidence_ids": sorted(set(int(value) for value in row["referenced_evidence_ids"])),
                "final_review_decision_id": int(row["final_review_decision_id"]),
                "completion_record_sha256": str(row["completion_record_sha256"]),
            }
        )

    competencies = []
    for entry in grouped.values():
        practica = sorted(
            entry["practica"],
            key=lambda item: (
                item["completed_at"],
                item["template_slug"],
                item["template_version"],
                item["enrollment_id"],
            ),
        )
        competencies.append(
            {
                "competency_key": entry["competency_key"],
                "competency_label": entry["competency_label"],
                "completed_practicum_count": len(practica),
                "practica": practica,
            }
        )

    portfolio = {
        "schema": PORTFOLIO_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "learner_user_id": learner_user_id,
        "generated_at": _utc_z(generated_at),
        "competencies": sorted(competencies, key=lambda item: item["competency_key"]),
        "excluded_record_count": excluded_record_count,
        "advisory_notice": ADVISORY_NOTICE,
    }
    findings = validate_portfolio(portfolio)
    if findings:
        raise ValueError("Invalid learner competency portfolio: " + "; ".join(findings))
    return portfolio


def build_receipt(portfolio: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_portfolio(portfolio)
    if findings:
        raise ValueError("Cannot receipt invalid learner competency portfolio: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "portfolio_sha256": sha256_digest(portfolio),
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
            if _PRIVATE_FIELDS.search(str(key)):
                findings.append(f"prohibited private-content field at {child_path}")
            findings.extend(_scan_private_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_scan_private_fields(child, f"{path}[{index}]"))
    return findings


def validate_portfolio(portfolio: Any) -> list[str]:
    findings: list[str] = []
    if not isinstance(portfolio, dict):
        return ["portfolio must be an object"]
    findings.extend(f"unexpected portfolio field: {field}" for field in sorted(set(portfolio) - _PORTFOLIO_FIELDS))
    findings.extend(f"missing portfolio field: {field}" for field in sorted(_PORTFOLIO_FIELDS - set(portfolio)))
    if portfolio.get("schema") != PORTFOLIO_SCHEMA:
        findings.append("unsupported portfolio schema")
    if portfolio.get("schema_version") != SCHEMA_VERSION:
        findings.append("unsupported portfolio schema version")
    if portfolio.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported portfolio generator version")
    if portfolio.get("advisory_notice") != ADVISORY_NOTICE:
        findings.append("portfolio advisory notice mismatch")
    if not _valid_timestamp(portfolio.get("generated_at")):
        findings.append("generated_at must be a UTC Z timestamp")
    if not isinstance(portfolio.get("learner_user_id"), int) or portfolio.get("learner_user_id", 0) <= 0:
        findings.append("learner_user_id must be a positive integer")
    if not isinstance(portfolio.get("excluded_record_count"), int) or portfolio.get("excluded_record_count", -1) < 0:
        findings.append("excluded_record_count must be a nonnegative integer")

    competencies = portfolio.get("competencies")
    if not isinstance(competencies, list):
        findings.append("competencies must be a list")
    else:
        expected = sorted(competencies, key=lambda item: item.get("competency_key", "") if isinstance(item, dict) else "")
        if competencies != expected:
            findings.append("competencies must use deterministic key ordering")
        keys = [item.get("competency_key") for item in competencies if isinstance(item, dict)]
        if len(keys) != len(set(keys)):
            findings.append("duplicate competency_key")
        seen_enrollments: set[tuple[str, int]] = set()
        for competency in competencies:
            if not isinstance(competency, dict):
                findings.append("competency must be an object")
                continue
            if set(competency) != {"competency_key", "competency_label", "completed_practicum_count", "practica"}:
                findings.append("competency fields are invalid")
            practica = competency.get("practica")
            if not isinstance(practica, list):
                findings.append("practica must be a list")
                continue
            if competency.get("completed_practicum_count") != len(practica):
                findings.append("completed_practicum_count mismatch")
            expected_practica = sorted(
                practica,
                key=lambda item: (
                    item.get("completed_at", ""),
                    item.get("template_slug", ""),
                    item.get("template_version", 0),
                    item.get("enrollment_id", 0),
                ),
            )
            if practica != expected_practica:
                findings.append("practica must use deterministic ordering")
            for practicum in practica:
                if not isinstance(practicum, dict):
                    findings.append("practicum must be an object")
                    continue
                if set(practicum) != {
                    "enrollment_id",
                    "template_slug",
                    "template_version",
                    "research_project_id",
                    "completed_at",
                    "objective_keys",
                    "referenced_evidence_ids",
                    "final_review_decision_id",
                    "completion_record_sha256",
                }:
                    findings.append("practicum fields are invalid")
                enrollment_key = (str(competency.get("competency_key")), practicum.get("enrollment_id"))
                if enrollment_key in seen_enrollments:
                    findings.append("duplicate practicum enrollment within competency")
                seen_enrollments.add(enrollment_key)
                if not _valid_timestamp(practicum.get("completed_at")):
                    findings.append("practicum completed_at must be a UTC Z timestamp")
                objective_keys = practicum.get("objective_keys")
                if not isinstance(objective_keys, list) or objective_keys != sorted(set(objective_keys)):
                    findings.append("objective_keys must be unique and sorted")
                evidence_ids = practicum.get("referenced_evidence_ids")
                if not isinstance(evidence_ids, list) or evidence_ids != sorted(set(evidence_ids)):
                    findings.append("referenced_evidence_ids must be unique and sorted")
                digest = practicum.get("completion_record_sha256")
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    findings.append("completion_record_sha256 must be a lowercase SHA-256 digest")

    findings.extend(_scan_private_fields(portfolio))
    return sorted(set(findings))


def validate_receipt(receipt: Any, portfolio: Any) -> list[str]:
    findings = validate_portfolio(portfolio)
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
    digest = receipt.get("portfolio_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        findings.append("portfolio_sha256 must be a lowercase SHA-256 digest")
    elif isinstance(portfolio, dict) and digest != sha256_digest(portfolio):
        findings.append("portfolio digest mismatch")
    findings.extend(_scan_private_fields(receipt))
    return sorted(set(findings))
