from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.education import LessonProgress
from app.models.research_practicum import (
    PracticumEnrollment,
    PracticumObjective,
    PracticumObjectiveProgress,
    PracticumTemplate,
)
from app.models.research_project import ResearchProject
from app.models.user import User
from app.services.learner_competency_gap_plan import sha256_digest as gap_plan_sha256
from app.services.learner_competency_gap_plan_export import export_competency_gap_plan
from app.services.roadmap_practicum_enrollment_receipt import build_action, build_receipt, validate_receipt

MAX_MISSING_PREREQUISITES = 25


def start_recommended_practicum(
    db: Session,
    *,
    user: User,
    template_slug: str,
    template_version: int,
    research_project_id: int,
    acted_at: datetime | None = None,
) -> dict[str, Any]:
    now = acted_at or datetime.now(timezone.utc)
    roadmap_bundle = export_competency_gap_plan(db, user=user, generated_at=now)
    plan = roadmap_bundle["plan"]
    plan_digest = gap_plan_sha256(plan)

    recommendation = next(
        (
            item
            for item in plan["recommendations"]
            if item["template_slug"] == template_slug and item["template_version"] == template_version
        ),
        None,
    )
    if recommendation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Roadmap recommendation is stale or unavailable"},
        )

    template = db.scalar(
        select(PracticumTemplate).where(
            PracticumTemplate.slug == template_slug,
            PracticumTemplate.version == template_version,
            PracticumTemplate.status == "active",
        )
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Roadmap recommendation is stale or unavailable"},
        )

    objectives = list(
        db.scalars(
            select(PracticumObjective)
            .where(PracticumObjective.template_id == template.id)
            .order_by(PracticumObjective.sequence, PracticumObjective.objective_key)
        ).all()
    )
    current_objective_keys = sorted({objective.objective_key for objective in objectives})
    current_competency_keys = sorted({objective.competency for objective in objectives})
    if (
        current_objective_keys != recommendation["objective_keys"]
        or current_competency_keys != recommendation["competency_keys"]
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Roadmap recommendation metadata changed; refresh the roadmap"},
        )

    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == research_project_id,
            ResearchProject.owner_id == user.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research project not found")

    completed_lesson_slugs = set(
        db.scalars(
            select(LessonProgress.lesson_slug).where(
                LessonProgress.user_id == user.id,
                LessonProgress.status == "completed",
            )
        ).all()
    )
    missing = sorted(
        slug for slug in recommendation["prerequisite_lesson_slugs"] if slug not in completed_lesson_slugs
    )
    if missing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Practicum prerequisites are incomplete",
                "missing_lesson_slugs": missing[:MAX_MISSING_PREREQUISITES],
            },
        )

    enrollment = PracticumEnrollment(
        user_id=user.id,
        template_id=template.id,
        template_version=template.version,
        research_project_id=project.id,
        status="in_progress",
        started_at=now.replace(tzinfo=None),
    )
    db.add(enrollment)
    try:
        db.flush()
        for objective in objectives:
            db.add(
                PracticumObjectiveProgress(
                    enrollment_id=enrollment.id,
                    objective_key=objective.objective_key,
                )
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Practicum enrollment already exists"},
        ) from exc

    db.refresh(enrollment)
    action = build_action(
        learner_user_id=user.id,
        enrollment_id=enrollment.id,
        enrollment_status=enrollment.status,
        template_slug=template.slug,
        template_version=template.version,
        research_project_id=project.id,
        recommendation_reason_codes=recommendation["reason_codes"],
        roadmap_plan_sha256=plan_digest,
        portfolio_sha256=plan["portfolio_sha256"],
        acted_at=now,
    )
    return {
        "action": action,
        "receipt": build_receipt(action, generated_at=now),
    }


def validate_roadmap_enrollment_bundle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"action", "receipt"}:
        return {"valid": False, "findings": ["bundle fields are invalid"]}
    findings = validate_receipt(payload.get("receipt"), payload.get("action"))
    return {"valid": not findings, "findings": findings}
