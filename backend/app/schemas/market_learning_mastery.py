from typing import Literal

from pydantic import BaseModel


class MarketLearningMasteryDimension(BaseModel):
    key: Literal[
        "scenario_breadth",
        "risk_tier_comparison",
        "evidence_discipline",
        "review_follow_through",
        "contradiction_handling",
        "reflection_quality",
    ]
    title: str
    status: Literal["not_started", "developing", "met"]
    evidence_count: int
    target_count: int
    criteria: str
    unmet_criteria: list[str]
    next_action: str


class MarketLearningMasteryRead(BaseModel):
    overall_readiness: Literal["not_started", "foundational", "developing", "evidence_informed"]
    dimensions_met: int
    dimensions_total: int
    calculation_criteria: list[str]
    dimensions: list[MarketLearningMasteryDimension]
    disclaimer: str
