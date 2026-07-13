from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class KnowledgeEntityAlias(Base):
    __tablename__ = "knowledge_entity_aliases"
    __table_args__ = (
        UniqueConstraint("owner_id", "normalized_alias", name="uq_entity_alias_owner_normalized"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    entity_id: Mapped[int] = mapped_column(ForeignKey("knowledge_entities.id", ondelete="CASCADE"), index=True, nullable=False)
    alias: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    alias_type: Mapped[str] = mapped_column(String(32), default="name", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class KnowledgeEntityMergeAudit(Base):
    __tablename__ = "knowledge_entity_merge_audits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    canonical_entity_id: Mapped[int] = mapped_column(ForeignKey("knowledge_entities.id", ondelete="CASCADE"), index=True, nullable=False)
    merged_entity_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    moved_relationship_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_alias_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
