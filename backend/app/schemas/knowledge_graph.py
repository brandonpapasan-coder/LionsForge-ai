from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KnowledgeEntityCreate(BaseModel):
    entity_type: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    validation_status: str = Field(default="unverified", pattern="^(unverified|validated|disputed|archived)$")
    provenance: dict = Field(default_factory=dict)
    attributes: dict = Field(default_factory=dict)


class KnowledgeEntityRead(KnowledgeEntityCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class KnowledgeRelationshipCreate(BaseModel):
    source_entity_id: int
    target_entity_id: int
    relationship_type: str = Field(min_length=1, max_length=80)
    description: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    validation_status: str = Field(default="unverified", pattern="^(unverified|validated|disputed|archived)$")
    provenance: dict = Field(default_factory=dict)
    attributes: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_self_relationship(self):
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("source and target entities must be different")
        return self


class KnowledgeRelationshipRead(KnowledgeRelationshipCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class KnowledgeGraphRead(BaseModel):
    entities: list[KnowledgeEntityRead]
    relationships: list[KnowledgeRelationshipRead]
