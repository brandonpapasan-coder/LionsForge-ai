from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.evidence_intelligence import EvidenceReviewEventRead


class RTIComponent(BaseModel):
    key: str
    label: str
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    weighted_score: float = Field(ge=0, le=100)
    explanation: str
    recommendations: list[str] = Field(default_factory=list)


class ResearchTrustIndexRead(BaseModel):
    project_id: int
    overall_score: float = Field(ge=0, le=100)
    confidence_level: str
    evidence_count: int
    supporting_count: int
    contradicting_count: int
    approved_count: int
    conflict_count: int
    review_event_count: int
    reviewed_evidence_count: int
    review_reversal_count: int
    components: list[RTIComponent]
    strengths: list[str]
    limitations: list[str]
    recommended_actions: list[str]
    methodology_version: str = "rti-v2"


class GovernanceExecutiveSummary(BaseModel):
    trust_status: str
    risk_level: str
    headline: str
    evidence_review_rate: float = Field(ge=0, le=1)
    approval_rate: float = Field(ge=0, le=1)
    key_strengths: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    priority_actions: list[str] = Field(default_factory=list)


class ProjectGovernanceSnapshotRead(BaseModel):
    project_id: int
    project_title: str
    project_status: str
    generated_at: datetime
    executive_summary: GovernanceExecutiveSummary
    trust_index: ResearchTrustIndexRead
    review_history: list[EvidenceReviewEventRead] = Field(default_factory=list)
