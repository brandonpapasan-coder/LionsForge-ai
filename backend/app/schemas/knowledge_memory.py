from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryStatus = Literal["provisional", "validated", "contested", "superseded", "archived"]
UserAuthoredMemoryCategory = Literal[
    "research_preference",
    "research_context",
    "learning_goal",
    "mentor_preference",
    "mastery_signal",
    "misconception",
]


class KnowledgeMemoryCreate(BaseModel):
    project_id: int
    statement: str = Field(min_length=1, max_length=4000)
    summary: str = Field(min_length=1, max_length=1000)
    category: UserAuthoredMemoryCategory
    confidence: float = Field(default=0.5, ge=0, le=1)
    source_evidence_ids: list[int] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)


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
    mission_id: int | None
    snapshot_id: int | None
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


class KnowledgeMemoryEvidenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    source_url: str | None
    source_title: str
    publisher: str | None
    author: str | None
    published_at: datetime | None
    source_type: str
    claim: str
    excerpt: str
    stance: str
    credibility_score: float
    freshness_score: float
    confidence_score: float
    validation_status: str


class KnowledgeMemoryEvidenceTrace(BaseModel):
    memory_id: int
    requested_evidence_ids: list[int]
    evidence: list[KnowledgeMemoryEvidenceItem]
    unavailable_evidence_ids: list[int]


class KnowledgeMemoryPromotionResult(BaseModel):
    memories: list[KnowledgeMemoryRead]
    created_count: int
    reused_count: int


class KnowledgeMemoryControlSummary(BaseModel):
    project_id: int | None
    total_count: int
    active_count: int
    archived_count: int
    user_authored_count: int
    research_generated_count: int
    revision_count: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    available_controls: list[str]


class KnowledgeMemorySynthesis(BaseModel):
    project_id: int
    validated: list[KnowledgeMemoryRead]
    provisional: list[KnowledgeMemoryRead]
    contested: list[KnowledgeMemoryRead]
    superseded: list[KnowledgeMemoryRead]
    agreements: list[str]
    contradictions: list[str]
    unresolved_questions: list[str]
