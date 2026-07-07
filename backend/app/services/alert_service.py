from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertEvaluation
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


def evaluate_alert(alert: Alert) -> AlertEvaluation:
    quote = get_quote(alert.symbol)
    triggered = quote.price >= alert.target_price if alert.condition == "above" else quote.price <= alert.target_price
    return AlertEvaluation(
        alert_id=alert.id,
        symbol=alert.symbol,
        condition=alert.condition,
        target_price=alert.target_price,
        current_price=quote.price,
        triggered=triggered,
    )


def evaluate_alerts(db: Session, owner_id: int) -> list[AlertEvaluation]:
    alerts = list(db.scalars(select(Alert).where(Alert.owner_id == owner_id, Alert.is_active.is_(True))))
    return [evaluate_alert(alert) for alert in alerts]
