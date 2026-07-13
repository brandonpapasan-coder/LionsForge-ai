from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class KnowledgeFederationLink(Base):
    __tablename__ = "knowledge_federation_links"
    __table_args__ = (
        UniqueConstraint("owner_id", "fingerprint", name="uq_knowledge_federation_link"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    source_memory_id: Mapped[int] = mapped_column(ForeignKey("knowledge_memories.id", ondelete="CASCADE"), index=True, nullable=False)
    target_memory_id: Mapped[int] = mapped_column(ForeignKey("knowledge_memories.id", ondelete="CASCADE"), index=True, nullable=False)
    source_project_id: Mapped[int] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    target_project_id: Mapped[int] = mapped_column(ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    link_type: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    score_components: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="proposed", index=True, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    revision_number: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class KnowledgeFederationRevision(Base):
    __tablename__ = "knowledge_federation_revisions"
    __table_args__ = (
        UniqueConstraint("link_id", "revision_number", name="uq_knowledge_federation_revision"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    link_id: Mapped[int] = mapped_column(ForeignKey("knowledge_federation_links.id", ondelete="CASCADE"), index=True, nullable=False)
    revision_number: Mapped[int] = mapped_column(nullable=False)
    link_type: Mapped[str] = mapped_column(String(24), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    score_components: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
