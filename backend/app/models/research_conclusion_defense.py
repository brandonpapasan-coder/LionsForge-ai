from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ResearchConclusionDefense(Base):
    __tablename__ = "research_conclusion_defenses"
    __table_args__ = (
        UniqueConstraint("owner_id", "project_id", name="uq_research_conclusion_defense_owner_project"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    conclusion_revision_number: Mapped[int | None] = mapped_column(nullable=True)
    evidence_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    evidence_coverage: Mapped[str] = mapped_column(Text, default="", nullable=False)
    strongest_counterargument: Mapped[str] = mapped_column(Text, default="", nullable=False)
    known_limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)
    unresolved_questions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence_rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="incomplete", index=True, nullable=False)
    missing_sections: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    revision_count: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ResearchConclusionDefenseRevision(Base):
    __tablename__ = "research_conclusion_defense_revisions"
    __table_args__ = (
        UniqueConstraint("defense_id", "revision_number", name="uq_research_conclusion_defense_revision_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    defense_id: Mapped[int] = mapped_column(ForeignKey("research_conclusion_defenses.id", ondelete="CASCADE"), index=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    revision_number: Mapped[int] = mapped_column(nullable=False)
    conclusion_revision_number: Mapped[int | None] = mapped_column(nullable=True)
    evidence_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    evidence_coverage: Mapped[str] = mapped_column(Text, nullable=False)
    strongest_counterargument: Mapped[str] = mapped_column(Text, nullable=False)
    known_limitations: Mapped[str] = mapped_column(Text, nullable=False)
    unresolved_questions: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    missing_sections: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    revision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
