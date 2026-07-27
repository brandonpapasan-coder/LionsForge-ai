from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.learner_competency_portfolio_export import (
    export_competency_portfolio,
    validate_competency_portfolio_bundle,
)

router = APIRouter()


@router.get("")
def get_learner_competency_portfolio(
    competency_key: str | None = Query(default=None, max_length=120),
    template_slug: str | None = Query(default=None, max_length=120),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return export_competency_portfolio(
        db,
        user=current_user,
        competency_key=competency_key,
        template_slug=template_slug,
    )


@router.post("/validate")
def validate_learner_competency_portfolio(
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    return validate_competency_portfolio_bundle(payload)
