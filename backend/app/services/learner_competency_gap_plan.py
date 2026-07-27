from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

PLAN_SCHEMA = "lionsforge.learner-competency-gap-plan"
RECEIPT_SCHEMA = "lionsforge.learner-competency-gap-plan-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
MAX_RECOMMENDATIONS = 12
DEMONSTRATED_THRESHOLD = 2
ADVISORY_NOTICE = (
    "This deterministic educational roadmap summarizes evidence-backed learning gaps and next-practice options. "
    "It is not accreditation, licensing, degree equivalence, professional certification, employment qualification, "
    "individualized financial advice, or autonomous competency approval."
)

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


def _status(count: int) -> str:
    if count >= DEMONSTRATED_THRESHOLD:
        return "demonstrated"
    if count == 1:
        return "developing"
    return "not_yet_demonstrated"


def build_plan(
    *,
    learner_user_id: int,
    generated_at: datetime,
    portfolio_sha256: str,
    competency_rows: list[dict[str, Any]],
    template_rows: list[dict[str, Any]],
    completed_template_versions: set[tuple[str, int]],
) -> dict[str, Any]:
    competencies: list[dict[str, Any]] = []
    count_by_key: dict[str, int] = {}
    label_by_key: dict[str, str] = {}
    for row in competency_rows:
        key = str(row["competency_key"])
        count = int(row["completed_practicum_count"])
        count_by_key[key] = count
        label_by_key[key] = str(row["competency_label"])
        competencies.append(
            {
                "competency_key": key,
                "competency_label": label_by_key[key],
                "supporting_completed_practicum_count": count,
                "status": _status(count),
            }
        )

    recommendations: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for template in template_rows:
        slug = str(template["template_slug"])
        version = int(template["template_version"])
        identity = (slug, version)
        if identity in seen or identity in completed_template_versions:
            continue
        seen.add(identity)
        objective_keys = sorted(set(str(value) for value in template["objective_keys"]))
        competency_keys = sorted(set(str(value) for value in template["competency_keys"]))
        statuses = [_status(count_by_key.get(key, 0)) for key in competency_keys]
        if statuses and all(status == "demonstrated" for status in statuses):
            continue
        reason_codes: list[str] = []
        if any(status == "not_yet_demonstrated" for status in statuses):
            reason_codes.append("adds_not_yet_demonstrated_competency")
        if any(status == "developing" for status in statuses):
            reason_codes.append("strengthens_developing_competency")
        recommendations.append(
            {
                "template_slug": slug,
                "template_version": version,
                "objective_keys": objective_keys,
                "competency_keys": competency_keys,
                "estimated_minutes": int(template["estimated_minutes"]),
                "prerequisite_lesson_slugs": sorted(
                    set(str(value) for value in template.get("prerequisite_lesson_slugs", []))
                ),
                "reason_codes": reason_codes,
            }
        )

    recommendations.sort(
        key=lambda item: (
            0 if "adds_not_yet_demonstrated_competency" in item["reason_codes"] else 1,
            item["estimated_minutes"],
            item["template_slug"],
            item["template_version"],
        )
    )
    plan = {
        "schema": PLAN_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "learner_user_id": learner_user_id,
        "generated_at": _utc_z(generated_at),
        "portfolio_sha256": portfolio_sha256,
        "thresholds": {"demonstrated_minimum_completed_practica": DEMONSTRATED_THRESHOLD},
        "competencies": sorted(competencies, key=lambda item: item["competency_key"]),
        "recommendations": recommendations[:MAX_RECOMMENDATIONS],
        "advisory_notice": ADVISORY_NOTICE,
    }
    findings = validate_plan(plan)
    if findings:
        raise ValueError("Invalid learner competency gap plan: " + "; ".join(findings))
    return plan


def build_receipt(plan: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_plan(plan)
    if findings:
        raise ValueError("Cannot receipt invalid learner competency gap plan: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "plan_sha256": sha256_digest(plan),
        "portfolio_sha256": plan["portfolio_sha256"],
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


def validate_plan(plan: Any) -> list[str]:
    required = {
        "schema", "schema_version", "generator_version", "learner_user_id", "generated_at",
        "portfolio_sha256", "thresholds", "competencies", "recommendations", "advisory_notice",
    }
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    findings: list[str] = []
    findings.extend(f"unexpected plan field: {field}" for field in sorted(set(plan) - required))
    findings.extend(f"missing plan field: {field}" for field in sorted(required - set(plan)))
    if plan.get("schema") != PLAN_SCHEMA:
        findings.append("unsupported plan schema")
    if plan.get("schema_version") != SCHEMA_VERSION:
        findings.append("unsupported plan schema version")
    if plan.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported plan generator version")
    if plan.get("advisory_notice") != ADVISORY_NOTICE:
        findings.append("plan advisory notice mismatch")
    if not _valid_timestamp(plan.get("generated_at")):
        findings.append("generated_at must be a UTC Z timestamp")
    digest = plan.get("portfolio_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        findings.append("portfolio_sha256 must be a lowercase SHA-256 digest")
    if plan.get("thresholds") != {"demonstrated_minimum_completed_practica": DEMONSTRATED_THRESHOLD}:
        findings.append("unsupported competency thresholds")
    competencies = plan.get("competencies")
    if not isinstance(competencies, list):
        findings.append("competencies must be a list")
    else:
        if competencies != sorted(competencies, key=lambda item: item.get("competency_key", "")):
            findings.append("competencies must use deterministic key ordering")
        keys = [item.get("competency_key") for item in competencies if isinstance(item, dict)]
        if len(keys) != len(set(keys)):
            findings.append("duplicate competency_key")
        for item in competencies:
            if not isinstance(item, dict) or set(item) != {
                "competency_key", "competency_label", "supporting_completed_practicum_count", "status"
            }:
                findings.append("competency fields are invalid")
                continue
            count = item.get("supporting_completed_practicum_count")
            if not isinstance(count, int) or count < 0 or item.get("status") != _status(count):
                findings.append("competency status does not match deterministic threshold")
    recommendations = plan.get("recommendations")
    if not isinstance(recommendations, list) or len(recommendations) > MAX_RECOMMENDATIONS:
        findings.append("recommendations must be a bounded list")
    else:
        identities: list[tuple[Any, Any]] = []
        for item in recommendations:
            if not isinstance(item, dict):
                findings.append("recommendation must be an object")
                continue
            identities.append((item.get("template_slug"), item.get("template_version")))
            if item.get("objective_keys") != sorted(set(item.get("objective_keys", []))):
                findings.append("recommendation objective_keys must be unique and sorted")
            if item.get("competency_keys") != sorted(set(item.get("competency_keys", []))):
                findings.append("recommendation competency_keys must be unique and sorted")
            if item.get("prerequisite_lesson_slugs") != sorted(set(item.get("prerequisite_lesson_slugs", []))):
                findings.append("recommendation prerequisites must be unique and sorted")
            reasons = item.get("reason_codes")
            allowed = {"adds_not_yet_demonstrated_competency", "strengthens_developing_competency"}
            if not isinstance(reasons, list) or not reasons or not set(reasons).issubset(allowed):
                findings.append("recommendation reason_codes are invalid")
        if len(identities) != len(set(identities)):
            findings.append("duplicate recommendation template version")
    findings.extend(_scan_private_fields(plan))
    return sorted(set(findings))


def validate_receipt(receipt: Any, plan: Any) -> list[str]:
    findings = validate_plan(plan)
    required = {"schema", "schema_version", "generator_version", "plan_sha256", "portfolio_sha256", "generated_at"}
    if not isinstance(receipt, dict):
        return sorted(set(findings + ["receipt must be an object"]))
    findings.extend(f"unexpected receipt field: {field}" for field in sorted(set(receipt) - required))
    findings.extend(f"missing receipt field: {field}" for field in sorted(required - set(receipt)))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append("unsupported receipt schema")
    if not _valid_timestamp(receipt.get("generated_at")):
        findings.append("receipt generated_at must be a UTC Z timestamp")
    if isinstance(plan, dict):
        if receipt.get("plan_sha256") != sha256_digest(plan):
            findings.append("plan digest mismatch")
        if receipt.get("portfolio_sha256") != plan.get("portfolio_sha256"):
            findings.append("portfolio digest binding mismatch")
    findings.extend(_scan_private_fields(receipt))
    return sorted(set(findings))
