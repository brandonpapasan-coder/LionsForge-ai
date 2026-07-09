from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AlertNotification(Base):
    __tablename__ = "alert_notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), nullable=True, index=True)
    symbol: Mapped[str | None] = mapped_column(String(12), index=True, nullable=True)
    notification_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_channel: Mapped[str] = mapped_column(String(32), default="in_app", nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(32), default="delivered", nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
