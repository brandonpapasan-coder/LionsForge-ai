from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class MarketLearningProgressRead(BaseModel):
    total_sessions: int
    completed_sessions: int
    unique_scenarios: int
    scenario_counts: dict[str, int]
    risk_tier_counts: dict[str, int]
    average_projected_return: Decimal
    latest_completed_at: datetime | None
    proficiency_level: Literal["not_started", "foundational", "developing", "proficient"]
    evidence_badge_eligible: bool
    next_learning_step: str
    disclaimer: str
