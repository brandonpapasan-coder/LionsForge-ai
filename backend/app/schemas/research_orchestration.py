from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ResearchRole = Literal["research", "evidence", "risk", "synthesis"]
ConfidenceLevel = Literal["low", "moderate", "high"]


class ResearchOrchestrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=8000)
    project_id: int | None = Field(default=None, gt=0)
    symbol: str | None = Field(default=None, min_length=1, max_length=20)
    context: dict[str, object] = Field(default_factory=dict)
    requested_roles: list[ResearchRole] | None = Field(default=None, min_length=1, max_length=4)


class ResearchPlanStep(BaseModel):
    order: int = Field(gt=0)
    role: ResearchRole
    objective: str = Field(min_length=1, max_length=500)


class ResearchAgentOutput(BaseModel):
    role: ResearchRole
    summary: str = Field(min_length=1, max_length=2000)
    findings: list[str] = Field(default_factory=list, max_length=20)
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    evidence_gaps: list[str] = Field(default_factory=list, max_length=20)
    confidence: ConfidenceLevel


class ResearchSynthesis(BaseModel):
    conclusion: str = Field(min_length=1, max_length=4000)
    key_drivers: list[str] = Field(default_factory=list, max_length=20)
    alternative_viewpoints: list[str] = Field(default_factory=list, max_length=20)
    recommended_actions: list[str] = Field(default_factory=list, max_length=20)


class ResearchOrchestrationResponse(BaseModel):
    run_id: str
    question: str
    project_id: int | None
    symbol: str | None
    plan: list[ResearchPlanStep]
    agent_outputs: list[ResearchAgentOutput]
    synthesis: ResearchSynthesis
    evidence_gaps: list[str]
    assumptions: list[str]
    confidence: ConfidenceLevel
