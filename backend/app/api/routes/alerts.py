from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertEvaluation, AlertRead
from app.services.alert_service import create_alert, evaluate_alerts, list_alerts

router = APIRouter()


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
def create_alert_endpoint(
    payload: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertRead:
    return create_alert(db, owner_id=current_user.id, payload=payload)


@router.get("", response_model=list[AlertRead])
def list_alerts_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertRead]:
    return list_alerts(db, owner_id=current_user.id)


@router.get("/evaluate", response_model=list[AlertEvaluation])
def evaluate_alerts_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertEvaluation]:
    return evaluate_alerts(db, owner_id=current_user.id)
