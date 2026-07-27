from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research_practicum import PracticumEnrollment
from app.models.roadmap_action_record import RoadmapActionRecord
from app.models.user import User
from app.services.practicum_completion_export import export_completion_bundle
from app.services.practicum_completion_audit import validate_receipt as validate_completion_receipt
from app.services.roadmap_action_outcome_report import build_receipt, build_report, validate_entry, validate_receipt

MAX_QUERY_ROWS = 225


def export_roadmap_action_outcomes(
    db: Session,
    *,
    user: User,
    generated_at: datetime | None = None,
    template_slug: str | None = None,
    reason_code: str | None = None,
    outcome_status: str | None = None,
    acted_after: datetime | None = None,
    acted_before: datetime | None = None,
    completed_after: datetime | None = None,
    completed_before: datetime | None = None,
) -> dict[str, Any]:
    now = generated_at or datetime.now(timezone.utc)
    query = (
        select(RoadmapActionRecord, PracticumEnrollment)
        .join(PracticumEnrollment, PracticumEnrollment.id == RoadmapActionRecord.enrollment_id)
        .where(RoadmapActionRecord.learner_user_id == user.id)
        .order_by(RoadmapActionRecord.acted_at.desc(), RoadmapActionRecord.enrollment_id.desc())
        .limit(MAX_QUERY_ROWS)
    )
    if template_slug:
        query = query.where(RoadmapActionRecord.template_slug == template_slug)
    if outcome_status:
        query = query.where(PracticumEnrollment.status == outcome_status)
    if acted_after:
        query = query.where(RoadmapActionRecord.acted_at >= acted_after.replace(tzinfo=None))
    if acted_before:
        query = query.where(RoadmapActionRecord.acted_at <= acted_before.replace(tzinfo=None))
    if completed_after:
        query = query.where(PracticumEnrollment.completed_at >= completed_after.replace(tzinfo=None))
    if completed_before:
        query = query.where(PracticumEnrollment.completed_at <= completed_before.replace(tzinfo=None))

    entries: list[dict[str, Any]] = []
    excluded: list[str] = []
    excluded_count = 0
    for record, enrollment in db.execute(query).all():
        reasons = sorted(set(str(value) for value in record.recommendation_reason_codes))
        if reason_code and reason_code not in reasons:
            continue
        completed_at = None
        completion_record_sha256 = None
        try:
            if enrollment.status == "completed":
                bundle = export_completion_bundle(db, enrollment_id=enrollment.id, user=user, generated_at=now)
                findings = validate_completion_receipt(bundle["receipt"], bundle["record"])
                if findings:
                    raise ValueError("completion audit validation failed")
                completed_at = enrollment.completed_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
                completion_record_sha256 = bundle["receipt"]["record_sha256"]
            entry = {
                "learner_user_id": record.learner_user_id,
                "enrollment_id": record.enrollment_id,
                "outcome_status": enrollment.status,
                "template_slug": record.template_slug,
                "template_version": record.template_version,
                "research_project_id": record.research_project_id,
                "recommendation_reason_codes": reasons,
                "action_sha256": record.action_sha256,
                "action_receipt_sha256": record.action_receipt_sha256,
                "acted_at": record.acted_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                "completed_at": completed_at,
                "completion_record_sha256": completion_record_sha256,
            }
            findings = validate_entry(entry, learner_user_id=user.id)
            if findings:
                raise ValueError("; ".join(findings))
            entries.append(entry)
        except (KeyError, TypeError, ValueError, AttributeError):
            excluded_count += 1
            excluded.extend([f"record {record.id}: stored outcome failed integrity requirements"])

    report = build_report(
        learner_user_id=user.id,
        generated_at=now,
        entries=entries,
        excluded_record_count=excluded_count,
        excluded_findings=excluded,
    )
    return {"report": report, "receipt": build_receipt(report, generated_at=now)}


def validate_roadmap_action_outcome_bundle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"report", "receipt"}:
        return {"valid": False, "findings": ["bundle fields are invalid"]}
    findings = validate_receipt(payload.get("receipt"), payload.get("report"))
    return {"valid": not findings, "findings": findings}
