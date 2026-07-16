from datetime import datetime

from pydantic import BaseModel, Field


class MarketLearningPortfolioClaim(BaseModel):
    session_id: int
    evidence_id: int
    scenario_name: str
    risk_tier: str
    claim: str
    validation_status: str
    reviewer_notes: str | None
    review_event_count: int = Field(ge=0)
    next_reflection_prompt: str
    completed_at: datetime


class MarketLearningPortfolioRead(BaseModel):
    completed_sessions: int = Field(ge=0)
    unique_scenarios: int = Field(ge=0)
    scenario_counts: dict[str, int]
    risk_tier_counts: dict[str, int]
    submitted_evidence: int = Field(ge=0)
    validation_status_counts: dict[str, int]
    immutable_review_events: int = Field(ge=0)
    learning_maturity: str
    maturity_criteria: list[str]
    recent_claims: list[MarketLearningPortfolioClaim]
    disclaimer: str
