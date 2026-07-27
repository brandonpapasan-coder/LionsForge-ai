from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.roadmap_action_outcome_export import export_roadmap_action_outcomes
from app.services.roadmap_action_outcome_report import validate_receipt as validate_outcome_receipt
from app.services.roadmap_outcome_insights import build_insights, build_receipt, validate_receipt


def export_roadmap_outcome_insights(
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
    source_bundle = export_roadmap_action_outcomes(
        db,
        user=user,
        generated_at=now,
        template_slug=template_slug,
        reason_code=reason_code,
        outcome_status=outcome_status,
        acted_after=acted_after,
        acted_before=acted_before,
        completed_after=completed_after,
        completed_before=completed_before,
    )
    source_findings = validate_outcome_receipt(source_bundle["receipt"], source_bundle["report"])
    if source_findings:
        raise ValueError("Canonical roadmap outcome source failed integrity validation")
    if source_bundle["report"].get("learner_user_id") != user.id:
        raise ValueError("Canonical roadmap outcome source learner binding mismatch")

    insights = build_insights(source_report=source_bundle["report"], generated_at=now)
    return {
        "insights": insights,
        "receipt": build_receipt(insights, generated_at=now),
    }


def validate_roadmap_outcome_insight_bundle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"insights", "receipt"}:
        return {"valid": False, "findings": ["bundle fields are invalid"]}
    findings = validate_receipt(payload.get("receipt"), payload.get("insights"))
    return {"valid": not findings, "findings": findings}
