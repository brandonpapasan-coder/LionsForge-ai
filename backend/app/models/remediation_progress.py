from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RemediationProgress(Base):
    __tablename__ = "remediation_progress"
    __table_args__ = (
        UniqueConstraint(
            "investigation_id",
            "claim_id",
            "owner_id",
            name="uq_remediation_progress_investigation_claim_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("investigation_claims.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_type_snapshot: Mapped[str] = mapped_column(String(48), nullable=False)
    priority_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_generated_at_snapshot: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
