from typing import Literal

from pydantic import BaseModel, Field

ReadinessState = Literal["blocked", "needs_review", "ready_for_user_conclusion"]
CheckLevel = Literal["blocking", "caution", "informational"]

class ReadinessCheck(BaseModel):
    code: str
    level: CheckLevel
    passed: bool
    message: str
    evidence_ids: list[int] = Field(default_factory=list)
    action_ids: list[int] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    governing_rules: list[str] = Field(default_factory=list)

class ResearchConclusionReadiness(BaseModel):
    project_id: int
    state: ReadinessState
    evidence_count: int
    blocking_count: int
    caution_count: int
    checks: list[ReadinessCheck]
    next_steps: list[str]
    disclaimer: str
