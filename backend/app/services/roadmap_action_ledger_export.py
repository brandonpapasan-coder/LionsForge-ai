from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research_practicum import PracticumEnrollment
from app.models.roadmap_action_record import RoadmapActionRecord
from app.models.user import User
from app.services.roadmap_action_ledger import build_ledger, build_receipt, validate_entry, validate_receipt

MAX_QUERY_ROWS = 225


def export_roadmap_action_ledger(
    db: Session,
    *,
    user: User,
    generated_at: datetime | None = None,
    template_slug: str | None = None,
    reason_code: str | None = None,
    acted_after: datetime | None = None,
    acted_before: datetime | None = None,
) -> dict[str, Any]:
    now = generated_at or datetime.now(timezone.utc)
    query = (
        select(RoadmapActionRecord, PracticumEnrollment.status)
        .join(PracticumEnrollment, PracticumEnrollment.id == RoadmapActionRecord.enrollment_id)
        .where(RoadmapActionRecord.learner_user_id == user.id)
        .order_by(RoadmapActionRecord.acted_at.desc(), RoadmapActionRecord.enrollment_id.desc())
        .limit(MAX_QUERY_ROWS)
    )
    if template_slug:
        query = query.where(RoadmapActionRecord.template_slug == template_slug)
    if acted_after:
        query = query.where(RoadmapActionRecord.acted_at >= acted_after.replace(tzinfo=None))
    if acted_before:
        query = query.where(RoadmapActionRecord.acted_at <= acted_before.replace(tzinfo=None))

    entries: list[dict[str, Any]] = []
    excluded: list[str] = []
    excluded_count = 0
    for record, enrollment_status in db.execute(query).all():
        reasons = sorted(set(str(value) for value in record.recommendation_reason_codes))
        if reason_code and reason_code not in reasons:
            continue
        acted_at = record.acted_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        entry = {
            "learner_user_id": record.learner_user_id,
            "enrollment_id": record.enrollment_id,
            "enrollment_status": enrollment_status,
            "template_slug": record.template_slug,
            "template_version": record.template_version,
            "research_project_id": record.research_project_id,
            "recommendation_reason_codes": reasons,
            "roadmap_plan_sha256": record.roadmap_plan_sha256,
            "portfolio_sha256": record.portfolio_sha256,
            "action_sha256": record.action_sha256,
            "action_receipt_sha256": record.action_receipt_sha256,
            "acted_at": acted_at,
        }
        findings = validate_entry(entry, learner_user_id=user.id)
        if findings:
            excluded_count += 1
            excluded.extend(f"record {record.id}: {finding}" for finding in findings)
            continue
        entries.append(entry)

    ledger = build_ledger(
        learner_user_id=user.id,
        generated_at=now,
        entries=entries,
        excluded_findings=excluded,
        excluded_record_count=excluded_count,
    )
    return {"ledger": ledger, "receipt": build_receipt(ledger, generated_at=now)}


def validate_roadmap_action_ledger_bundle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"ledger", "receipt"}:
        return {"valid": False, "findings": ["bundle fields are invalid"]}
    findings = validate_receipt(payload.get("receipt"), payload.get("ledger"))
    return {"valid": not findings, "findings": findings}
