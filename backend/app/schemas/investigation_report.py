from datetime import datetime

from pydantic import BaseModel


class ReportEvidence(BaseModel):
    id: int
    source_title: str
    source_url: str
    evidence_type: str
    relationship: str
    notes: str | None
    credibility_rating: str | None
    credibility_rationale: str | None


class ReportClaim(BaseModel):
    id: int
    statement: str
    confidence_level: str | None
    confidence_rationale: str | None
    supporting_count: int
    contradicting_count: int
    neutral_count: int
    has_unresolved_contradiction: bool
    evidence: list[ReportEvidence]


class InvestigationValidationReport(BaseModel):
    investigation_id: int
    title: str
    research_question: str
    status: str
    findings: str | None
    limitations: str | None
    unresolved_questions: str | None
    generated_from_updated_at: datetime
    user_authored_assessments: bool = True
    automated_truth_determination: bool = False
    claim_count: int
    unresolved_contradiction_count: int
    claims: list[ReportClaim]
