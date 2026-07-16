from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ImpactLevel = Literal["high_attention", "review_required", "informational"]
DigestCategory = Literal["newly_opened", "overdue", "reopened", "deferred", "recently_resolved"]
DigestCadence = Literal["daily", "weekly", "monthly"]


class ResearchGovernanceDigestPreferenceInput(BaseModel):
    project_ids: list[int] = []
    impact_levels: list[ImpactLevel] = ["high_attention", "review_required", "informational"]
    window_days: int = Field(default=30, ge=1, le=365)
    cadence: DigestCadence = "weekly"


class ResearchGovernanceDigestPreference(ResearchGovernanceDigestPreferenceInput):
    id: int
    created_at: datetime
    updated_at: datetime


class ResearchGovernanceDigestItem(BaseModel):
    category: DigestCategory
    severity_rank: int
    action_id: int
    project_id: int
    evidence_id: int
    impact_level: ImpactLevel
    governing_rule: str
    status: str
    reason: str
    action_text: str
    supporting_event_ids: list[str]
    age_days: int
    reopen_count: int
    created_at: datetime
    updated_at: datetime


class ResearchGovernanceDigestSummary(BaseModel):
    newly_opened: int
    overdue: int
    reopened: int
    deferred: int
    recently_resolved: int
    total_items: int


class ResearchGovernanceDigest(BaseModel):
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    project_ids: list[int]
    impact_levels: list[ImpactLevel]
    summary: ResearchGovernanceDigestSummary
    items: list[ResearchGovernanceDigestItem]
    content_sha256: str
    disclaimer: str


class ResearchGovernanceDigestSnapshotItem(BaseModel):
    id: int
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    content_sha256: str
    item_count: int
    summary: dict


class ResearchGovernanceDigestHistory(BaseModel):
    snapshots: list[ResearchGovernanceDigestSnapshotItem]
