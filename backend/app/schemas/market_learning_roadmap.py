from typing import Literal

from pydantic import BaseModel


class MarketLearningRoadmapTask(BaseModel):
    task_key: str
    task_type: Literal["resolve_evidence", "submit_evidence", "explore_scenario", "compare_risk_tier"]
    priority: int
    title: str
    rationale: str
    completion_criteria: str
    reflection_prompt: str
    scenario_name: str | None = None
    risk_tier: str | None = None
    session_id: int | None = None
    evidence_id: int | None = None


class MarketLearningRoadmapRead(BaseModel):
    status: Literal["not_started", "active", "complete"]
    calculation_criteria: list[str]
    tasks: list[MarketLearningRoadmapTask]
    disclaimer: str
