from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class InvestigationSynthesisUpdate(BaseModel):
    findings: str | None = Field(default=None, max_length=20000)
    limitations: str | None = Field(default=None, max_length=12000)
    unresolved_questions: str | None = Field(default=None, max_length=12000)

    @field_validator("findings", "limitations", "unresolved_questions")
    @classmethod
    def normalize_sections(cls, value: str | None) -> str | None:
        return _normalize_optional(value)


class InvestigationSynthesisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_id: int
    findings: str | None
    limitations: str | None
    unresolved_questions: str | None
    created_at: datetime
    updated_at: datetime
    authorship: str = "user_authored"


class ReportEvidence(BaseModel):
    id: int
    source_title: str
    source_url: str
    evidence_type: str
    relationship: str
    credibility_rating: str | None
    credibility_rationale: str | None
    notes: str | None


class ReportJudgment(BaseModel):
    validation_status: str
    confidence_level: str
    rationale: str
    unresolved_questions: str | None
    reviewed_at: datetime
    is_stale: bool
    authorship: str = "user_judgment"


class ReportClaim(BaseModel):
    id: int
    statement: str
    confidence_level: str | None
    confidence_rationale: str | None
    relationship_counts: dict[str, int]
    evidence: list[ReportEvidence]
    latest_judgment: ReportJudgment | None
    has_unresolved_contradiction: bool


class InvestigationValidationReport(BaseModel):
    contract_version: str = "1.0"
    investigation_id: int
    title: str
    research_question: str
    investigation_status: str
    synthesis: InvestigationSynthesisRead | None
    claims: list[ReportClaim]
    aggregate_relationship_counts: dict[str, int]
    limitations: list[str]
    unresolved_questions: list[str]
    generated_from_stored_state_at: datetime
    interpretation_notice: str = (
        "This report organizes stored evidence and user-entered judgments. "
        "It does not present user judgments as automated truth."
    )


class QualityAssessmentDimension(BaseModel):
    key: str
    label: str
    status: Literal["missing", "partial", "complete"]
    counts: dict[str, int]
    explanation: str


class InvestigationQualityAssessment(BaseModel):
    contract_version: str = "1.0"
    investigation_id: int
    dimensions: list[QualityAssessmentDimension]
    recommendations: list[str]
    generated_from_stored_state_at: datetime
    interpretation_notice: str = (
        "This checklist describes research completeness from stored state. "
        "It is not a truth score, confidence probability, or automated validation judgment."
    )
