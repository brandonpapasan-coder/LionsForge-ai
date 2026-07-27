from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.roadmap_outcome_trend_export import (
    export_roadmap_outcome_trends,
    validate_roadmap_outcome_trend_bundle,
)

router = APIRouter()


@router.get("")
def get_roadmap_outcome_trends(
    granularity: Literal["day", "week", "month"] = Query(...),
    range_start: datetime = Query(...),
    range_end: datetime = Query(...),
    template_slug: str | None = Query(default=None, min_length=1, max_length=120),
    reason_code: str | None = Query(default=None, min_length=1, max_length=80),
    outcome_status: str | None = Query(default=None, pattern="^(not_started|in_progress|review_ready|completed)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return export_roadmap_outcome_trends(
        db,
        user=current_user,
        granularity=granularity,
        range_start=range_start,
        range_end=range_end,
        template_slug=template_slug,
        reason_code=reason_code,
        outcome_status=outcome_status,
    )


@router.post("/validate")
def validate_roadmap_outcome_trends(
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return validate_roadmap_outcome_trend_bundle(payload)
