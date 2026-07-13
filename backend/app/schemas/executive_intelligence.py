from typing import Literal

from pydantic import BaseModel, Field


class ExecutiveFact(BaseModel):
    statement: str
    evidence_ids: list[int]
    verified: bool
    confidence: float = Field(ge=0, le=1)


class ExecutiveRisk(BaseModel):
    category: str
    summary: str
    severity: Literal["low", "medium", "high", "critical"]
    evidence_ids: list[int]


class DecisionReadinessBreakdown(BaseModel):
    evidence_quality: float = Field(ge=0, le=100)
    consensus_strength: float = Field(ge=0, le=100)
    validation_coverage: float = Field(ge=0, le=100)
    conflict_penalty: float = Field(ge=0, le=100)


class ExecutiveIntelligenceBriefRead(BaseModel):
    project_id: int
    project_title: str
    objective: str | None
    recommendation: Literal["go", "hold", "investigate", "insufficient_evidence"]
    decision_readiness_score: float = Field(ge=0, le=100)
    readiness_breakdown: DecisionReadinessBreakdown
    research_trust_index: float = Field(ge=0, le=100)
    consensus_status: str
    overall_confidence: float = Field(ge=0, le=1)
    executive_summary: str
    verified_facts: list[ExecutiveFact]
    provisional_conclusions: list[str]
    assumptions: list[str]
    risks: list[ExecutiveRisk]
    minority_findings: list[str]
    unresolved_questions: list[str]
    recommended_actions: list[str]
    source_evidence_ids: list[int]
    methodology_version: str
