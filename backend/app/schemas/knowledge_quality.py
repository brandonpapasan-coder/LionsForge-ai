from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeQualityCounts(BaseModel):
    total: int = 0
    validated: int = 0
    provisional: int = 0
    contested: int = 0
    superseded: int = 0
    archived: int = 0
    stale: int = 0


class KnowledgeQualityMissions(BaseModel):
    total: int = 0
    draft: int = 0
    active: int = 0
    blocked: int = 0
    completed: int = 0


class KnowledgeQualityPlanning(BaseModel):
    total: int = 0
    proposed: int = 0
    accepted: int = 0
    completed: int = 0
    dismissed: int = 0
    archived: int = 0


class KnowledgeQualityRisk(BaseModel):
    risk_type: str
    severity: float = Field(ge=0, le=1)
    title: str
    detail: str
    source_ids: list[int] = Field(default_factory=list)


class KnowledgeQualityActivity(BaseModel):
    record_type: str
    record_id: int
    title: str
    status: str
    occurred_at: datetime


class KnowledgeQualityDashboard(BaseModel):
    project_id: int | None
    methodology_version: str
    generated_at: datetime
    health_score: float = Field(ge=0, le=1)
    health_components: dict[str, float]
    memories: KnowledgeQualityCounts
    evidence_total: int
    evidence_approved: int
    evidence_pending_review: int
    evidence_coverage_ratio: float
    average_confidence: float
    median_confidence: float
    contradiction_rate: float
    unresolved_contradictions: int
    federation_links: int
    federation_coverage_ratio: float
    missions: KnowledgeQualityMissions
    planning: KnowledgeQualityPlanning
    knowledge_revision_velocity: int
    review_backlog: int
    top_risks: list[KnowledgeQualityRisk]
    top_priorities: list[dict]
    recent_activity: list[KnowledgeQualityActivity]
