from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

ACTION_SCHEMA = "lionsforge.roadmap-practicum-enrollment-action"
RECEIPT_SCHEMA = "lionsforge.roadmap-practicum-enrollment-action-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
ACTION_SOURCE = "explicit_learner_request"
ADVISORY_NOTICE = (
    "This action records an explicit learner request to start a currently recommended research practicum. "
    "It is not accreditation, licensing, degree equivalence, professional certification, employment "
    "qualification, individualized financial advice, or autonomous competency approval."
)

_ACTION_FIELDS = {
    "schema",
    "schema_version",
    "generator_version",
    "action_source",
    "learner_user_id",
    "enrollment_id",
    "enrollment_status",
    "template_slug",
    "template_version",
    "research_project_id",
    "recommendation_reason_codes",
    "roadmap_plan_sha256",
    "portfolio_sha256",
    "acted_at",
    "advisory_notice",
}
_RECEIPT_FIELDS = {
    "schema",
    "schema_version",
    "generator_version",
    "action_sha256",
    "roadmap_plan_sha256",
    "portfolio_sha256",
    "generated_at",
}
_ALLOWED_REASONS = {
    "adds_not_yet_demonstrated_competency",
    "strengthens_developing_competency",
}
_PRIVATE_FIELDS = re.compile(
    r"(?:prompt|reflection|summary|reviewer[_-]?notes|answer[_-]?key|private[_-]?content|credential|project[_-]?title)",
    re.IGNORECASE,
)
_DIGEST = re.compile(r"[0-9a-f]{64}")


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _utc_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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


def build_action(
    *,
    learner_user_id: int,
    enrollment_id: int,
    enrollment_status: str,
    template_slug: str,
    template_version: int,
    research_project_id: int,
    recommendation_reason_codes: list[str],
    roadmap_plan_sha256: str,
    portfolio_sha256: str,
    acted_at: datetime,
) -> dict[str, Any]:
    action = {
        "schema": ACTION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "action_source": ACTION_SOURCE,
        "learner_user_id": learner_user_id,
        "enrollment_id": enrollment_id,
        "enrollment_status": enrollment_status,
        "template_slug": template_slug,
        "template_version": template_version,
        "research_project_id": research_project_id,
        "recommendation_reason_codes": sorted(set(recommendation_reason_codes)),
        "roadmap_plan_sha256": roadmap_plan_sha256,
        "portfolio_sha256": portfolio_sha256,
        "acted_at": _utc_z(acted_at),
        "advisory_notice": ADVISORY_NOTICE,
    }
    findings = validate_action(action)
    if findings:
        raise ValueError("Invalid roadmap enrollment action: " + "; ".join(findings))
    return action


def build_receipt(action: dict[str, Any], *, generated_at: datetime) -> dict[str, Any]:
    findings = validate_action(action)
    if findings:
        raise ValueError("Cannot receipt invalid roadmap enrollment action: " + "; ".join(findings))
    return {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "action_sha256": sha256_digest(action),
        "roadmap_plan_sha256": action["roadmap_plan_sha256"],
        "portfolio_sha256": action["portfolio_sha256"],
        "generated_at": _utc_z(generated_at),
    }


def validate_action(action: Any) -> list[str]:
    if not isinstance(action, dict):
        return ["action must be an object"]
    findings: list[str] = []
    findings.extend(f"unexpected action field: {field}" for field in sorted(set(action) - _ACTION_FIELDS))
    findings.extend(f"missing action field: {field}" for field in sorted(_ACTION_FIELDS - set(action)))
    if action.get("schema") != ACTION_SCHEMA:
        findings.append("unsupported action schema")
    if action.get("schema_version") != SCHEMA_VERSION:
        findings.append("unsupported action schema version")
    if action.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported action generator version")
    if action.get("action_source") != ACTION_SOURCE:
        findings.append("action source must record explicit learner intent")
    if action.get("advisory_notice") != ADVISORY_NOTICE:
        findings.append("action advisory notice mismatch")
    for field in ("learner_user_id", "enrollment_id", "template_version", "research_project_id"):
        if not isinstance(action.get(field), int) or action.get(field, 0) <= 0:
            findings.append(f"{field} must be a positive integer")
    if action.get("enrollment_status") not in {"not_started", "in_progress"}:
        findings.append("unsupported enrollment status")
    if not isinstance(action.get("template_slug"), str) or not action.get("template_slug", "").strip():
        findings.append("template_slug must be non-empty")
    reasons = action.get("recommendation_reason_codes")
    if (
        not isinstance(reasons, list)
        or not reasons
        or reasons != sorted(set(reasons))
        or not set(reasons).issubset(_ALLOWED_REASONS)
    ):
        findings.append("recommendation reason codes are invalid")
    for field in ("roadmap_plan_sha256", "portfolio_sha256"):
        if not isinstance(action.get(field), str) or not _DIGEST.fullmatch(action[field]):
            findings.append(f"{field} must be a lowercase SHA-256 digest")
    if not _valid_timestamp(action.get("acted_at")):
        findings.append("acted_at must be a UTC Z timestamp")
    findings.extend(_scan_private_fields(action))
    return sorted(set(findings))


def validate_receipt(receipt: Any, action: Any) -> list[str]:
    findings = validate_action(action)
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
    if isinstance(action, dict):
        if receipt.get("action_sha256") != sha256_digest(action):
            findings.append("action digest mismatch")
        if receipt.get("roadmap_plan_sha256") != action.get("roadmap_plan_sha256"):
            findings.append("roadmap digest binding mismatch")
        if receipt.get("portfolio_sha256") != action.get("portfolio_sha256"):
            findings.append("portfolio digest binding mismatch")
    findings.extend(_scan_private_fields(receipt))
    return sorted(set(findings))
