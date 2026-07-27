from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.roadmap_action_outcome_export import export_roadmap_action_outcomes
from app.services.roadmap_action_outcome_report import validate_receipt as validate_outcome_receipt
from app.services.roadmap_outcome_trends import build_receipt, build_trends, validate_receipt


def export_roadmap_outcome_trends(
    db: Session,
    *,
    user: User,
    granularity: Literal["day", "week", "month"],
    range_start: datetime,
    range_end: datetime,
    generated_at: datetime | None = None,
    template_slug: str | None = None,
    reason_code: str | None = None,
    outcome_status: str | None = None,
) -> dict[str, Any]:
    now = generated_at or datetime.now(timezone.utc)
    source_bundle = export_roadmap_action_outcomes(
        db,
        user=user,
        generated_at=now,
        template_slug=template_slug,
        reason_code=reason_code,
        outcome_status=outcome_status,
        acted_after=range_start,
        acted_before=range_end,
    )
    source_findings = validate_outcome_receipt(source_bundle["receipt"], source_bundle["report"])
    if source_findings:
        raise ValueError("Canonical roadmap outcome source failed integrity validation")
    if source_bundle["report"].get("learner_user_id") != user.id:
        raise ValueError("Canonical roadmap outcome source learner binding mismatch")

    trends = build_trends(
        source_report=source_bundle["report"],
        granularity=granularity,
        range_start=range_start,
        range_end=range_end,
        generated_at=now,
    )
    return {"trends": trends, "receipt": build_receipt(trends, generated_at=now)}


def validate_roadmap_outcome_trend_bundle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"trends", "receipt"}:
        return {"valid": False, "findings": ["bundle fields are invalid"]}
    findings = validate_receipt(payload.get("receipt"), payload.get("trends"))
    return {"valid": not findings, "findings": findings}
