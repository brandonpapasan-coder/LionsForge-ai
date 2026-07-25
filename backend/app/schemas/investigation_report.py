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


class ValidationMapEvidenceLink(BaseModel):
    evidence_id: int
    source_title: str
    source_url: str
    evidence_type: str
    relationship: Literal["supporting", "contradicting", "contextual"]
    stored_relationship: Literal["supports", "contradicts", "neutral"]
    classification_rule: str
    credibility_rating: str | None
    credibility_rationale: str | None
    notes: str | None


class ValidationMapHumanReview(BaseModel):
    status: Literal["not_reviewed", "current", "stale"]
    validation_status: str | None
    confidence_level: str | None
    rationale: str | None
    unresolved_questions: str | None
    reviewed_at: datetime | None
    authorship: Literal["user_judgment"] = "user_judgment"


class ValidationMapClaim(BaseModel):
    claim_id: int
    sequence: int = Field(ge=1)
    statement: str
    status: Literal["supported", "contested", "insufficient", "unreviewed"]
    status_rule: str
    relationship_counts: dict[str, int]
    confidence_inputs: list[str]
    evidence_links: list[ValidationMapEvidenceLink]
    missing_evidence_requirements: list[str]
    unresolved_gaps: list[str]
    human_review: ValidationMapHumanReview


class ClaimEvidenceValidationMap(BaseModel):
    contract_version: str = "1.0"
    investigation_id: int
    title: str
    status: Literal["active", "empty"]
    claims: list[ValidationMapClaim]
    summary_counts: dict[str, int]
    unresolved_gaps: list[str]
    generated_from: Literal["stored_evidence_rules"] = "stored_evidence_rules"
    generated_from_stored_state_at: datetime
    interpretation_notice: str = (
        "Statuses organize recorded evidence through deterministic rules. "
        "They do not establish objective truth and must remain subject to human review."
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


class InvestigationEvidencePacket(BaseModel):
    contract_version: str = "1.0"
    export_format: Literal["json"] = "json"
    investigation_id: int
    validation_report: InvestigationValidationReport
    quality_assessment: InvestigationQualityAssessment
    generated_from_stored_state_at: datetime
    provenance_notice: str = (
        "This packet is assembled deterministically from stored investigation state. "
        "Synthesis text and validation judgments remain explicitly human-authored, and the packet does not assign truth."
    )