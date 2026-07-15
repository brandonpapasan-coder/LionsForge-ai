from hashlib import sha256

from sqlalchemy.orm import Session

from app.schemas.advanced_alert import AdvancedAlertCreate, AdvancedAlertRead
from app.services.alert_service import deliver_notification

_CATEGORY_LABELS = {
    "earnings": "Earnings event",
    "sec_filing": "SEC filing",
    "analyst_change": "Analyst change",
    "macro_event": "Macro event",
    "portfolio_risk": "Portfolio risk threshold",
}


def create_advanced_alert(db: Session, owner_id: int, payload: AdvancedAlertCreate) -> AdvancedAlertRead:
    symbol = payload.symbol.strip().upper() if payload.symbol else None
    title = f"{_CATEGORY_LABELS[payload.category]}: {payload.headline.strip()}"
    context_parts = [payload.detail.strip()]
    if payload.event_at is not None:
        context_parts.append(f"Event time: {payload.event_at.isoformat()}.")
    if payload.source_label:
        context_parts.append(f"Source: {payload.source_label.strip()}.")
    if payload.category == "portfolio_risk":
        context_parts.append(
            f"Portfolio {payload.portfolio_id} risk score {payload.risk_score} met threshold {payload.threshold}."
        )
    message = " ".join(context_parts)

    notification = deliver_notification(
        db=db,
        owner_id=owner_id,
        symbol=symbol,
        notification_type=payload.category,
        severity=payload.severity,
        title=title,
        message=message,
    )
    event_key = ":".join(
        [
            str(owner_id),
            payload.category,
            symbol or "",
            payload.headline.strip(),
            payload.event_at.isoformat() if payload.event_at else "",
            str(payload.portfolio_id or ""),
        ]
    )
    return AdvancedAlertRead(
        event_id=sha256(event_key.encode()).hexdigest()[:20],
        notification_id=notification.id,
        category=payload.category,
        symbol=symbol,
        severity=payload.severity,
        title=title,
        message=message,
        event_at=payload.event_at,
        source_label=payload.source_label.strip() if payload.source_label else None,
        delivery_status=notification.delivery_status,
        created_at=notification.created_at,
    )
