from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.roadmap_action_ledger_export import (
    export_roadmap_action_ledger,
    validate_roadmap_action_ledger_bundle,
)

router = APIRouter()


@router.get("")
def get_roadmap_action_ledger(
    template_slug: str | None = Query(default=None, min_length=1, max_length=120),
    reason_code: str | None = Query(default=None, min_length=1, max_length=80),
    acted_after: datetime | None = None,
    acted_before: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return export_roadmap_action_ledger(
        db,
        user=current_user,
        template_slug=template_slug,
        reason_code=reason_code,
        acted_after=acted_after,
        acted_before=acted_before,
    )


@router.post("/validate")
def validate_roadmap_action_ledger(
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return validate_roadmap_action_ledger_bundle(payload)
