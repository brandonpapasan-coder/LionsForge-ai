from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.advanced_alert import AdvancedAlertCreate, AdvancedAlertRead
from app.services.advanced_alert_service import create_advanced_alert

router = APIRouter()


@router.post("/events", response_model=AdvancedAlertRead, status_code=status.HTTP_201_CREATED)
def create_advanced_alert_endpoint(
    payload: AdvancedAlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdvancedAlertRead:
    return create_advanced_alert(db, owner_id=current_user.id, payload=payload)
