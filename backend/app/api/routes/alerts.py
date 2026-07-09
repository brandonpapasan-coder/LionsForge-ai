from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.alert import (
    AlertAutomationRuleCreate,
    AlertAutomationRuleRead,
    AlertCreate,
    AlertEvaluation,
    AlertNotificationRead,
    AlertRead,
    AutomationRunResult,
)
from app.services.alert_service import (
    create_alert,
    create_automation_rule,
    evaluate_alerts,
    list_alerts,
    list_automation_rules,
    list_notifications,
    mark_notification_read,
    run_automation_rule,
)

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


@router.get("/notifications", response_model=list[AlertNotificationRead])
def list_notifications_endpoint(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertNotificationRead]:
    return list_notifications(db, owner_id=current_user.id, unread_only=unread_only)


@router.post("/notifications/{notification_id}/read", response_model=AlertNotificationRead)
def mark_notification_read_endpoint(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertNotificationRead:
    notification = mark_notification_read(db, owner_id=current_user.id, notification_id=notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/automation-rules", response_model=AlertAutomationRuleRead, status_code=status.HTTP_201_CREATED)
def create_automation_rule_endpoint(
    payload: AlertAutomationRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertAutomationRuleRead:
    return create_automation_rule(db, owner_id=current_user.id, payload=payload)


@router.get("/automation-rules", response_model=list[AlertAutomationRuleRead])
def list_automation_rules_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertAutomationRuleRead]:
    return list_automation_rules(db, owner_id=current_user.id)


@router.post("/automation-rules/{rule_id}/run", response_model=AutomationRunResult)
def run_automation_rule_endpoint(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AutomationRunResult:
    result = run_automation_rule(db, owner_id=current_user.id, rule_id=rule_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automation rule not found")
    return result
