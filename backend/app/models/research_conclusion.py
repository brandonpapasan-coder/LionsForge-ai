from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ResearchConclusion(Base):
    __tablename__ = "research_conclusions"
    __table_args__ = (
        UniqueConstraint("owner_id", "project_id", name="uq_research_conclusion_owner_project"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True, nullable=False)
    conclusion_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ResearchConclusionRevision(Base):
    __tablename__ = "research_conclusion_revisions"
    __table_args__ = (
        UniqueConstraint("conclusion_id", "revision_number", name="uq_research_conclusion_revision_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conclusion_id: Mapped[int] = mapped_column(ForeignKey("research_conclusions.id", ondelete="CASCADE"), index=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    revision_number: Mapped[int] = mapped_column(nullable=False)
    conclusion_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    revision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
