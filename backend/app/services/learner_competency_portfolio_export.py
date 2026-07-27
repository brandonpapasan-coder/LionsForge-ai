from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research_practicum import PracticumEnrollment, PracticumObjective, PracticumTemplate
from app.models.user import User
from app.services.learner_competency_portfolio import build_portfolio, build_receipt, validate_receipt
from app.services.practicum_completion_export import export_completion_bundle

MAX_COMPLETED_PRACTICA = 200
MAX_EXCLUSION_FINDINGS = 25


def export_competency_portfolio(
    db: Session,
    *,
    user: User,
    competency_key: str | None = None,
    template_slug: str | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    filters = [
        PracticumEnrollment.user_id == user.id,
        PracticumEnrollment.status == "completed",
        PracticumEnrollment.completed_at.is_not(None),
    ]
    if template_slug and template_slug.strip():
        filters.append(PracticumTemplate.slug == template_slug.strip())

    enrollments = list(
        db.scalars(
            select(PracticumEnrollment)
            .join(PracticumTemplate, PracticumTemplate.id == PracticumEnrollment.template_id)
            .where(*filters)
            .order_by(PracticumEnrollment.completed_at, PracticumEnrollment.id)
            .limit(MAX_COMPLETED_PRACTICA)
        ).all()
    )

    rows: list[dict[str, Any]] = []
    exclusion_findings: list[dict[str, Any]] = []
    for enrollment in enrollments:
        try:
            bundle = export_completion_bundle(
                db,
                enrollment_id=enrollment.id,
                user=user,
                generated_at=generated_at,
            )
            validation = validate_receipt(bundle["receipt"], bundle["record"])
            if validation:
                raise ValueError("completion audit validation failed")

            objectives = list(
                db.scalars(
                    select(PracticumObjective)
                    .where(PracticumObjective.template_id == enrollment.template_id)
                    .order_by(PracticumObjective.sequence, PracticumObjective.objective_key)
                ).all()
            )
            objective_by_key = {objective.objective_key: objective for objective in objectives}
            record = bundle["record"]
            final_decision_id = record["review_history"][-1]["decision_id"]
            for record_objective in record["objectives"]:
                objective = objective_by_key.get(record_objective["objective_key"])
                if objective is None:
                    raise ValueError("objective context missing")
                if competency_key and objective.competency != competency_key:
                    continue
                rows.append(
                    {
                        "competency_key": objective.competency,
                        "competency_label": objective.competency.replace("_", " ").title(),
                        "enrollment_id": enrollment.id,
                        "template_slug": record["template_slug"],
                        "template_version": record["template_version"],
                        "research_project_id": record["research_project_id"],
                        "completed_at": enrollment.completed_at,
                        "objective_keys": [record_objective["objective_key"]],
                        "referenced_evidence_ids": record_objective["referenced_evidence_ids"],
                        "final_review_decision_id": final_decision_id,
                        "completion_record_sha256": bundle["receipt"]["record_sha256"],
                    }
                )
        except (KeyError, TypeError, ValueError):
            if len(exclusion_findings) < MAX_EXCLUSION_FINDINGS:
                exclusion_findings.append(
                    {
                        "enrollment_id": enrollment.id,
                        "reason": "completed practicum failed portfolio integrity requirements",
                    }
                )

    now = generated_at or datetime.now(timezone.utc)
    portfolio = build_portfolio(
        learner_user_id=user.id,
        generated_at=now,
        competency_rows=rows,
        excluded_record_count=len(exclusion_findings),
    )
    return {
        "portfolio": portfolio,
        "receipt": build_receipt(portfolio, generated_at=now),
        "exclusions": exclusion_findings,
    }


def validate_competency_portfolio_bundle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"portfolio", "receipt"}:
        return {"valid": False, "findings": ["bundle fields are invalid"]}
    findings = validate_receipt(payload.get("receipt"), payload.get("portfolio"))
    return {"valid": not findings, "findings": findings}
