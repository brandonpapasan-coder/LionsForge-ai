from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RecommendationStatus = Literal[
    "proposed",
    "accepted",
    "dismissed",
    "completed",
    "archived",
]


class ResearchPlanUpdate(BaseModel):
    status: RecommendationStatus | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    rationale: str | None = Field(default=None, min_length=1)
    recommended_action: str | None = Field(default=None, min_length=1)


class ResearchPlanRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    revision_number: int
    recommendation_type: str
    title: str
    rationale: str
    recommended_action: str
    priority_score: float
    priority_components: dict
    status: str
    mission_id: int | None
    provenance: dict
    created_at: datetime


class ResearchPlanRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    recommendation_type: str
    title: str
    rationale: str
    recommended_action: str
    priority_score: float
    priority_components: dict
    source_memory_ids: list[int]
    source_evidence_ids: list[int]
    source_federation_link_ids: list[int]
    provenance: dict
    status: str
    fingerprint: str
    mission_id: int | None
    revision_number: int
    created_at: datetime
    updated_at: datetime
    revisions: list[ResearchPlanRevisionRead] = Field(default_factory=list)


class ResearchPlanGenerationResult(BaseModel):
    recommendations: list[ResearchPlanRecommendationRead]
    created_count: int
    reused_count: int


class ResearchRoadmap(BaseModel):
    project_id: int
    total_recommendations: int
    proposed: list[ResearchPlanRecommendationRead]
    accepted: list[ResearchPlanRecommendationRead]
    completed: list[ResearchPlanRecommendationRead]
    dismissed: list[ResearchPlanRecommendationRead]
    archived: list[ResearchPlanRecommendationRead]
    top_priorities: list[ResearchPlanRecommendationRead]
