from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence_intelligence import EvidenceRead, EvidenceReviewEventRead


class MarketLearningEvidenceCreate(BaseModel):
    session_id: int = Field(gt=0)
    project_id: int = Field(gt=0)
    claim: str = Field(min_length=20, max_length=1000)
    stance: str = Field(default="supports", pattern="^(supports|contradicts|neutral)$")
    contradiction_key: str | None = Field(default=None, max_length=160)


class MarketLearningEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    link_id: int
    session_id: int
    project_id: int
    evidence: EvidenceRead
    scenario_name: str
    risk_tier: str
    simulated_projected_return: Decimal
    learner_reflection: str
    completed_at: datetime
    classification: str = "simulated_educational_evidence"
    next_reflection_prompt: str
    disclaimer: str


class MarketLearningEvidenceReviewHistory(BaseModel):
    evidence: MarketLearningEvidenceRead
    reviews: list[EvidenceReviewEventRead]
