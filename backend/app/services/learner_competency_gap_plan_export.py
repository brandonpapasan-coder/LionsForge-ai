from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research_practicum import PracticumEnrollment, PracticumObjective, PracticumTemplate
from app.models.user import User
from app.services.learner_competency_gap_plan import build_plan, build_receipt, validate_receipt
from app.services.learner_competency_portfolio_export import export_competency_portfolio

MAX_ACTIVE_TEMPLATES = 200


def export_competency_gap_plan(
    db: Session,
    *,
    user: User,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    now = generated_at or datetime.now(timezone.utc)
    portfolio_bundle = export_competency_portfolio(db, user=user, generated_at=now)
    portfolio = portfolio_bundle["portfolio"]
    portfolio_receipt = portfolio_bundle["receipt"]

    completed_template_versions = set(
        db.execute(
            select(PracticumTemplate.slug, PracticumEnrollment.template_version)
            .join(PracticumEnrollment, PracticumEnrollment.template_id == PracticumTemplate.id)
            .where(
                PracticumEnrollment.user_id == user.id,
                PracticumEnrollment.status == "completed",
            )
        ).all()
    )

    templates = list(
        db.scalars(
            select(PracticumTemplate)
            .where(PracticumTemplate.status == "active")
            .order_by(PracticumTemplate.slug, PracticumTemplate.version)
            .limit(MAX_ACTIVE_TEMPLATES)
        ).all()
    )

    template_rows: list[dict[str, Any]] = []
    for template in templates:
        objectives = list(
            db.scalars(
                select(PracticumObjective)
                .where(PracticumObjective.template_id == template.id)
                .order_by(PracticumObjective.sequence, PracticumObjective.objective_key)
            ).all()
        )
        if not objectives:
            continue
        template_rows.append(
            {
                "template_slug": template.slug,
                "template_version": template.version,
                "objective_keys": [objective.objective_key for objective in objectives],
                "competency_keys": [objective.competency for objective in objectives],
                "estimated_minutes": template.estimated_minutes,
                "prerequisite_lesson_slugs": template.prerequisite_lesson_slugs,
            }
        )

    plan = build_plan(
        learner_user_id=user.id,
        generated_at=now,
        portfolio_sha256=portfolio_receipt["portfolio_sha256"],
        competency_rows=[
            {
                "competency_key": competency["competency_key"],
                "competency_label": competency["competency_label"],
                "completed_practicum_count": competency["completed_practicum_count"],
            }
            for competency in portfolio["competencies"]
        ],
        template_rows=template_rows,
        completed_template_versions=completed_template_versions,
    )
    return {
        "plan": plan,
        "receipt": build_receipt(plan, generated_at=now),
        "source_portfolio": {
            "portfolio_sha256": portfolio_receipt["portfolio_sha256"],
            "excluded_record_count": portfolio["excluded_record_count"],
        },
    }


def validate_competency_gap_plan_bundle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"plan", "receipt"}:
        return {"valid": False, "findings": ["bundle fields are invalid"]}
    findings = validate_receipt(payload.get("receipt"), payload.get("plan"))
    return {"valid": not findings, "findings": findings}
