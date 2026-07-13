from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.knowledge_graph import KnowledgeEntityRead


class EntityAliasCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=200)
    alias_type: str = Field(default="name", pattern="^(name|ticker|abbreviation|historical|product)$")
    confidence: float = Field(default=1.0, ge=0, le=1)
    provenance: dict = Field(default_factory=dict)


class EntityAliasRead(EntityAliasCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    normalized_alias: str
    created_at: datetime


class DuplicateSuggestion(BaseModel):
    entity: KnowledgeEntityRead
    score: float = Field(ge=0, le=1)
    reasons: list[str]


class EntityMergeRequest(BaseModel):
    duplicate_entity_id: int
    reason: str | None = Field(default=None, max_length=500)


class EntityMergeResult(BaseModel):
    canonical_entity: KnowledgeEntityRead
    aliases_created: list[EntityAliasRead]
    relationships_moved: int
    audit_id: int
