from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ExecutiveBriefSnapshot(Base):
    __tablename__ = "executive_brief_snapshots"
    __table_args__ = (
        UniqueConstraint("owner_id", "project_id", "fingerprint", name="uq_executive_snapshot_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    decision_readiness_score: Mapped[float] = mapped_column(Float, nullable=False)
    research_trust_index: Mapped[float] = mapped_column(Float, nullable=False)
    consensus_status: Mapped[str] = mapped_column(String(32), nullable=False)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_evidence_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
