from typing import Literal

from pydantic import BaseModel, Field

ResearchRole = Literal["research", "evidence", "risk", "synthesis"]


class ResearchOrchestrationRequest(BaseModel):
    question: str = Field(min_length=3, max_length=8000)
    symbol: str | None = Field(default=None, min_length=1, max_length=20)
    context: dict = Field(default_factory=dict)
    requested_roles: list[ResearchRole] | None = None


class ResearchPlanStep(BaseModel):
    order: int
    role: ResearchRole
    objective: str


class ResearchAgentOutput(BaseModel):
    role: ResearchRole
    summary: str
    findings: list[str]
    assumptions: list[str]
    evidence_gaps: list[str]
    confidence: Literal["low", "moderate", "high"]


class ResearchSynthesis(BaseModel):
    conclusion: str
    key_drivers: list[str]
    alternative_viewpoints: list[str]
    recommended_actions: list[str]


class ResearchOrchestrationResponse(BaseModel):
    run_id: str
    question: str
    symbol: str | None
    plan: list[ResearchPlanStep]
    agent_outputs: list[ResearchAgentOutput]
    synthesis: ResearchSynthesis
    evidence_gaps: list[str]
    assumptions: list[str]
    confidence: Literal["low", "moderate", "high"]
