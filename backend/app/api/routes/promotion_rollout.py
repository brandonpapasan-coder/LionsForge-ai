from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.services.promotion_rollout import PromotionGateSnapshot
from app.services.promotion_rollout_status import read_promotion_rollout_status

router = APIRouter()


@router.get("/status")
def promotion_rollout_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator access required")

    gates = PromotionGateSnapshot(
        promotions_enabled=settings.promotions_enabled,
        paid_beta_authorized=settings.paid_beta_authorized,
        beta_lifetime_discount_enabled=settings.beta_lifetime_discount_enabled,
        founding_subscriber_enrollment_enabled=settings.founding_subscriber_enrollment_enabled,
        # Provider readiness remains false until a separately validated provider configuration is introduced.
        provider_ready=False,
    )
    return read_promotion_rollout_status(
        db,
        gates=gates,
        countdown_start_at=settings.promotion_countdown_start_at,
        countdown_launch_at=settings.promotion_countdown_launch_at,
        evaluated_at=datetime.now(UTC),
    ).to_dict()
