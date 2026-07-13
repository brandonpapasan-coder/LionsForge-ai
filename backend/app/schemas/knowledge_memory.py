from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryStatus = Literal["provisional", "validated", "contested", "superseded", "archived"]


class KnowledgeMemoryUpdate(BaseModel):
    statement: str | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    status: MemoryStatus | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_evidence_ids: list[int] | None = None


class KnowledgeMemoryRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    revision_number: int
    statement: str
    summary: str
    category: str
    status: str
    confidence: float
    source_evidence_ids: list[int]
    provenance: dict
    created_at: datetime


class KnowledgeMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    mission_id: int
    snapshot_id: int
    fingerprint: str
    statement: str
    summary: str
    category: str
    status: str
    confidence: float
    source_evidence_ids: list[int]
    provenance: dict
    superseded_by_id: int | None
    revision_number: int
    created_at: datetime
    updated_at: datetime
    revisions: list[KnowledgeMemoryRevisionRead] = Field(default_factory=list)


class KnowledgeMemoryPromotionResult(BaseModel):
    memories: list[KnowledgeMemoryRead]
    created_count: int
    reused_count: int


class KnowledgeMemorySynthesis(BaseModel):
    project_id: int
    validated: list[KnowledgeMemoryRead]
    provisional: list[KnowledgeMemoryRead]
    contested: list[KnowledgeMemoryRead]
    superseded: list[KnowledgeMemoryRead]
    agreements: list[str]
    contradictions: list[str]
    unresolved_questions: list[str]
