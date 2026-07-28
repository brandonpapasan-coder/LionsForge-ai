from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PaymentProviderValidation(Base):
    __tablename__ = "payment_provider_validations"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    configuration_digest: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    validated_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    api_reference_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    webhook_reference_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    price_references_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
