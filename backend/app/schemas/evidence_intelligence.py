from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class EvidenceCreate(BaseModel):
    project_id: int | None = None
    entity_id: int | None = None
    source_url: HttpUrl | None = None
    source_title: str = Field(min_length=1, max_length=300)
    publisher: str | None = Field(default=None, max_length=200)
    author: str | None = Field(default=None, max_length=200)
    published_at: datetime | None = None
    source_type: str = Field(default="secondary", pattern="^(primary|secondary|official|expert|user)$")
    claim: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)
    stance: str = Field(default="supports", pattern="^(supports|contradicts|neutral)$")
    contradiction_key: str | None = Field(default=None, max_length=160)
    provenance: dict = Field(default_factory=dict)


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    project_id: int | None
    entity_id: int | None
    source_url: str | None
    source_title: str
    publisher: str | None
    author: str | None
    published_at: datetime | None
    source_type: str
    claim: str
    excerpt: str
    stance: str
    contradiction_key: str | None
    fingerprint: str
    credibility_score: float
    freshness_score: float
    confidence_score: float
    validation_status: str
    reviewer_notes: str | None
    provenance: dict
    created_at: datetime
    updated_at: datetime


class EvidenceReview(BaseModel):
    validation_status: str = Field(pattern="^(unverified|approved|rejected|needs_review)$")
    reviewer_notes: str | None = None


class EvidenceReviewEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    evidence_id: int
    owner_id: int
    reviewer_id: int
    previous_status: str
    validation_status: str
    reviewer_notes: str | None
    created_at: datetime


class EvidenceConflictGroup(BaseModel):
    contradiction_key: str
    supporting: list[EvidenceRead]
    contradicting: list[EvidenceRead]
    neutral: list[EvidenceRead]
