from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research_practicum import (
    PracticumEnrollment,
    PracticumEvidenceReference,
    PracticumObjective,
    PracticumObjectiveProgress,
    PracticumReviewDecision,
    PracticumTemplate,
)
from app.models.user import User
from app.services.practicum_completion_audit import build_receipt, build_record, validate_receipt
from app.services.research_practicum_reviewer import readiness


def _completed_enrollment(db: Session, enrollment_id: int, user: User) -> PracticumEnrollment:
    enrollment = db.get(PracticumEnrollment, enrollment_id)
    if enrollment is None or (enrollment.user_id != user.id and not user.is_superuser):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Completed practicum not found")
    if enrollment.status != "completed" or enrollment.completed_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Practicum is not completed")
    return enrollment


def export_completion_bundle(
    db: Session,
    *,
    enrollment_id: int,
    user: User,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    enrollment = _completed_enrollment(db, enrollment_id, user)
    template = db.get(PracticumTemplate, enrollment.template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practicum context not found")

    readiness_result = readiness(db, enrollment)
    objectives = list(
        db.scalars(
            select(PracticumObjective)
            .where(PracticumObjective.template_id == enrollment.template_id)
            .order_by(PracticumObjective.sequence, PracticumObjective.objective_key)
        ).all()
    )
    progress_rows = list(
        db.scalars(
            select(PracticumObjectiveProgress).where(
                PracticumObjectiveProgress.enrollment_id == enrollment.id
            )
        ).all()
    )
    progress_by_key = {row.objective_key: row for row in progress_rows}
    readiness_by_key = {item.objective_key: item for item in readiness_result.objectives}

    objective_records: list[dict[str, Any]] = []
    for objective in objectives:
        progress = progress_by_key.get(objective.objective_key)
        result = readiness_by_key.get(objective.objective_key)
        if progress is None or result is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Practicum completion state is incomplete")
        evidence_ids = list(
            db.scalars(
                select(PracticumEvidenceReference.research_evidence_id)
                .where(PracticumEvidenceReference.objective_progress_id == progress.id)
                .order_by(PracticumEvidenceReference.research_evidence_id)
            ).all()
        )
        objective_records.append(
            {
                "objective_key": objective.objective_key,
                "sequence": objective.sequence,
                "status": result.status,
                "referenced_evidence_ids": evidence_ids,
            }
        )

    history = list(
        db.scalars(
            select(PracticumReviewDecision)
            .where(PracticumReviewDecision.enrollment_id == enrollment.id)
            .order_by(PracticumReviewDecision.created_at, PracticumReviewDecision.id)
        ).all()
    )
    record = build_record(
        enrollment_id=enrollment.id,
        learner_user_id=enrollment.user_id,
        template_slug=template.slug,
        template_version=enrollment.template_version,
        research_project_id=enrollment.research_project_id,
        completed_at=enrollment.completed_at,
        objectives=objective_records,
        review_history=[
            {
                "decision_id": row.id,
                "reviewer_user_id": row.reviewer_user_id,
                "decision": row.decision,
                "created_at": row.created_at,
            }
            for row in history
        ],
    )
    receipt = build_receipt(record, generated_at=generated_at or datetime.now(timezone.utc))
    return {"record": record, "receipt": receipt}


def validate_completion_bundle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"record", "receipt"}:
        return {"valid": False, "findings": ["bundle fields are invalid"]}
    findings = validate_receipt(payload.get("receipt"), payload.get("record"))
    return {"valid": not findings, "findings": findings}
