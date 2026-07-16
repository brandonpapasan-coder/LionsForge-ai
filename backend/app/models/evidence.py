from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    __table_args__ = (
        UniqueConstraint("owner_id", "fingerprint", name="uq_evidence_owner_fingerprint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_entities.id", ondelete="SET NULL"), index=True, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_title: Mapped[str] = mapped_column(String(300), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(200), nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="secondary", index=True, nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    stance: Mapped[str] = mapped_column(String(16), default="supports", index=True, nullable=False)
    contradiction_key: Mapped[str | None] = mapped_column(String(160), index=True, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    credibility_score: Mapped[float] = mapped_column(Float, nullable=False)
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(24), default="unverified", index=True, nullable=False)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EvidenceReviewEvent(Base):
    __tablename__ = "evidence_review_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    previous_status: Mapped[str] = mapped_column(String(24), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ResearchReviewAction(Base):
    __tablename__ = "research_review_actions"
    __table_args__ = (
        UniqueConstraint("owner_id", "action_key", name="uq_research_review_action_owner_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    evidence_id: Mapped[int] = mapped_column(index=True, nullable=False)
    action_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    impact_level: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    governing_rule: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_event_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="normal", index=True, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, index=True, nullable=True)
    owner_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ResearchReviewActionHistory(Base):
    __tablename__ = "research_review_action_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("research_review_actions.id", ondelete="CASCADE"), index=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    previous_status: Mapped[str] = mapped_column(String(24), nullable=False)
    new_status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ResearchGovernanceDigestPreference(Base):
    __tablename__ = "research_governance_digest_preferences"
    __table_args__ = (
        UniqueConstraint("owner_id", name="uq_research_governance_digest_preference_owner"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    impact_levels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    window_days: Mapped[int] = mapped_column(default=30, nullable=False)
    cadence: Mapped[str] = mapped_column(String(24), default="weekly", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ResearchGovernanceDigestSnapshot(Base):
    __tablename__ = "research_governance_digest_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    preference_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_governance_digest_preferences.id", ondelete="SET NULL"), index=True, nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    item_count: Mapped[int] = mapped_column(nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
