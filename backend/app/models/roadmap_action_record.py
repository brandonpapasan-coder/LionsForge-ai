from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RoadmapActionRecord(Base):
    __tablename__ = "roadmap_action_records"
    __table_args__ = (UniqueConstraint("enrollment_id", name="uq_roadmap_action_record_enrollment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    learner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("practicum_enrollments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    template_slug: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    research_project_id: Mapped[int] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recommendation_reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    roadmap_plan_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    portfolio_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    action_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    action_receipt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    action_schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    action_generator_version: Mapped[str] = mapped_column(String(32), nullable=False)
    acted_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
