from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.alert_automation_rule import AlertAutomationRule
from app.models.alert_notification import AlertNotification
from app.schemas.alert import (
    AlertAutomationRuleCreate,
    AlertCreate,
    AlertEvaluation,
    AutomationRunResult,
)
from app.services.market_data_service import get_quote


def create_alert(db: Session, owner_id: int, payload: AlertCreate) -> Alert:
    alert = Alert(
        owner_id=owner_id,
        symbol=payload.symbol.strip().upper(),
        condition=payload.condition.lower(),
        target_price=payload.target_price,
        note=payload.note,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def list_alerts(db: Session, owner_id: int) -> list[Alert]:
    statement = select(Alert).where(Alert.owner_id == owner_id).order_by(Alert.created_at.desc())
    return list(db.scalars(statement))


def deliver_notification(
    db: Session,
    owner_id: int,
    title: str,
    message: str,
    notification_type: str,
    severity: str = "info",
    symbol: str | None = None,
    alert_id: int | None = None,
) -> AlertNotification:
    notification = AlertNotification(
        owner_id=owner_id,
        alert_id=alert_id,
        symbol=symbol,
        notification_type=notification_type,
        severity=severity,
        title=title,
        message=message,
        delivery_channel="in_app",
        delivery_status="delivered",
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def evaluate_alert(db: Session, alert: Alert, deliver: bool = True) -> AlertEvaluation:
    quote = get_quote(alert.symbol)
    triggered = quote.price >= alert.target_price if alert.condition == "above" else quote.price <= alert.target_price
    notification_id: int | None = None
    if triggered and deliver:
        notification = deliver_notification(
            db=db,
            owner_id=alert.owner_id,
            alert_id=alert.id,
            symbol=alert.symbol,
            notification_type="price_alert",
            severity="warning",
            title=f"{alert.symbol} alert triggered",
            message=(
                f"{alert.symbol} is {quote.price} {quote.currency}, which is {alert.condition} "
                f"the configured target of {alert.target_price}."
            ),
        )
        notification_id = notification.id
    return AlertEvaluation(
        alert_id=alert.id,
        symbol=alert.symbol,
        condition=alert.condition,
        target_price=alert.target_price,
        current_price=quote.price,
        triggered=triggered,
        notification_id=notification_id,
    )


def evaluate_alerts(db: Session, owner_id: int, deliver: bool = True) -> list[AlertEvaluation]:
    alerts = list(db.scalars(select(Alert).where(Alert.owner_id == owner_id, Alert.is_active.is_(True))))
    return [evaluate_alert(db, alert, deliver=deliver) for alert in alerts]


def list_notifications(db: Session, owner_id: int, unread_only: bool = False) -> list[AlertNotification]:
    statement = select(AlertNotification).where(AlertNotification.owner_id == owner_id)
    if unread_only:
        statement = statement.where(AlertNotification.is_read.is_(False))
    statement = statement.order_by(AlertNotification.created_at.desc())
    return list(db.scalars(statement))


def mark_notification_read(db: Session, owner_id: int, notification_id: int) -> AlertNotification | None:
    notification = db.get(AlertNotification, notification_id)
    if notification is None or notification.owner_id != owner_id:
        return None
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)
    return notification


def create_automation_rule(db: Session, owner_id: int, payload: AlertAutomationRuleCreate) -> AlertAutomationRule:
    rule = AlertAutomationRule(
        owner_id=owner_id,
        name=payload.name.strip(),
        rule_type=payload.rule_type,
        schedule=payload.schedule,
        symbol=payload.symbol.strip().upper() if payload.symbol else None,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def list_automation_rules(db: Session, owner_id: int) -> list[AlertAutomationRule]:
    statement = select(AlertAutomationRule).where(AlertAutomationRule.owner_id == owner_id).order_by(
        AlertAutomationRule.created_at.desc()
    )
    return list(db.scalars(statement))


def run_automation_rule(db: Session, owner_id: int, rule_id: int) -> AutomationRunResult | None:
    rule = db.get(AlertAutomationRule, rule_id)
    if rule is None or rule.owner_id != owner_id or not rule.is_active:
        return None

    symbol = rule.symbol or "AAPL"
    quote = get_quote(symbol)
    if rule.rule_type == "daily_market_summary":
        title = f"Daily market summary for {symbol}"
        message = f"{symbol} latest quote is {quote.price} {quote.currency} from {quote.source}."
    elif rule.rule_type == "portfolio_review":
        title = "Portfolio review reminder"
        message = "Review portfolio allocation, open alerts, and latest research coverage."
    else:
        title = "Watchlist digest ready"
        message = f"Review watchlist activity and latest market context for {symbol}."

    notification = deliver_notification(
        db=db,
        owner_id=owner_id,
        symbol=symbol,
        notification_type=rule.rule_type,
        severity="info",
        title=title,
        message=message,
    )
    rule.last_run_at = datetime.utcnow()
    db.commit()
    return AutomationRunResult(rule_id=rule.id, notification_id=notification.id, title=title, delivery_status="delivered")
