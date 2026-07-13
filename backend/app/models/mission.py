from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    success_criteria: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True, nullable=False)
    current_step_order: Mapped[int] = mapped_column(default=0, nullable=False)
    final_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("executive_brief_snapshots.id", ondelete="SET NULL"), nullable=True
    )
    blocking_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology_version: Mapped[str] = mapped_column(String(64), default="mission-runtime-v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MissionStep(Base):
    __tablename__ = "mission_steps"
    __table_args__ = (
        UniqueConstraint("mission_id", "step_order", "attempt", name="uq_mission_step_attempt"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True, nullable=False)
    step_order: Mapped[int] = mapped_column(index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True, nullable=False)
    attempt: Mapped[int] = mapped_column(default=1, nullable=False)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    blocking_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology_version: Mapped[str] = mapped_column(String(64), default="mission-runtime-v1", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
