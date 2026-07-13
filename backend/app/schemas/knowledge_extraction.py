from pydantic import BaseModel, Field

from app.schemas.knowledge_graph import KnowledgeEntityRead, KnowledgeRelationshipRead


class KnowledgeExtractionRequest(BaseModel):
    content: str = Field(min_length=20, max_length=50000)
    source_title: str | None = Field(default=None, max_length=300)
    source_url: str | None = Field(default=None, max_length=2000)
    persist: bool = False


class ExtractedEntityCandidate(BaseModel):
    temporary_id: str
    entity_type: str
    name: str
    confidence: float = Field(ge=0, le=1)
    evidence: str


class ExtractedRelationshipCandidate(BaseModel):
    source_temporary_id: str
    target_temporary_id: str
    relationship_type: str
    confidence: float = Field(ge=0, le=1)
    evidence: str


class KnowledgeExtractionResponse(BaseModel):
    entities: list[ExtractedEntityCandidate]
    relationships: list[ExtractedRelationshipCandidate]
    persisted_entities: list[KnowledgeEntityRead] = Field(default_factory=list)
    persisted_relationships: list[KnowledgeRelationshipRead] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
