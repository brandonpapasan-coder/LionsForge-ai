from typing import Literal

from pydantic import BaseModel, Field

PersonalIntelligenceAudience = Literal["research_assistant", "ai_mentor"]


class PersonalIntelligenceContextRequest(BaseModel):
    audience: PersonalIntelligenceAudience
    project_id: int | None = None
    query: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=12, ge=1, le=50)
    include_provisional: bool = False


class PersonalIntelligenceContextItem(BaseModel):
    memory_id: int
    project_id: int
    category: str
    status: str
    confidence: float
    statement: str
    summary: str
    provenance: dict
    relevance_score: float


class PersonalIntelligenceContextResponse(BaseModel):
    audience: PersonalIntelligenceAudience
    memory_enabled: bool = True
    items: list[PersonalIntelligenceContextItem]
    trace_memory_ids: list[int]
