from pydantic import BaseModel, Field


class AgentFinding(BaseModel):
    agent: str
    conclusion: str
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[int]
    assumptions: list[str]
    limitations: list[str]
    recommended_actions: list[str]


class ConsensusConflict(BaseModel):
    key: str
    supporting_evidence_ids: list[int]
    contradicting_evidence_ids: list[int]
    summary: str


class MultiAgentConsensusRead(BaseModel):
    project_id: int
    consensus_status: str
    agreement_score: float = Field(ge=0, le=100)
    overall_confidence: float = Field(ge=0, le=1)
    research_trust_index: float = Field(ge=0, le=100)
    final_conclusion: str
    findings: list[AgentFinding]
    conflicts: list[ConsensusConflict]
    unresolved_questions: list[str]
    recommended_actions: list[str]
    methodology_version: str
