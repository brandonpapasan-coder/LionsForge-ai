from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EVIDENCE_TYPES = {"primary", "secondary", "dataset", "expert", "other"}
EVIDENCE_RELATIONSHIPS = {"supports", "contradicts", "neutral"}
ASSESSMENT_LEVELS = {"low", "medium", "high"}
VALIDATION_STATUSES = {"unreviewed", "supported", "mixed", "contradicted", "insufficient"}


def _required(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    return cleaned


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class ClaimCreate(BaseModel):
    statement: str = Field(min_length=1, max_length=4000)

    @field_validator("statement")
    @classmethod
    def validate_statement(cls, value: str) -> str:
        return _required(value, "claim")


class ClaimUpdate(ClaimCreate):
    pass


class ClaimAssessmentUpdate(BaseModel):
    confidence_level: str | None = None
    confidence_rationale: str | None = Field(default=None, max_length=4000)

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence_level(cls, value: str | None) -> str | None:
        if value is not None and value not in ASSESSMENT_LEVELS:
            raise ValueError("invalid confidence level")
        return value

    @field_validator("confidence_rationale")
    @classmethod
    def clean_confidence_rationale(cls, value: str | None) -> str | None:
        return _clean_optional(value)

    @model_validator(mode="after")
    def require_rationale_for_rating(self) -> "ClaimAssessmentUpdate":
        if self.confidence_level is not None and self.confidence_rationale is None:
            raise ValueError("confidence rationale is required when confidence is assessed")
        return self


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_id: int
    statement: str
    confidence_level: str | None
    confidence_rationale: str | None
    created_at: datetime
    updated_at: datetime


class EvidenceCreate(BaseModel):
    source_title: str = Field(min_length=1, max_length=240)
    source_url: str = Field(min_length=1, max_length=2048)
    evidence_type: str
    relationship: str
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("source_title")
    @classmethod
    def validate_source_title(cls, value: str) -> str:
        return _required(value, "source title")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        cleaned = _required(value, "source URL")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source URL must be an absolute HTTP or HTTPS URL")
        return cleaned

    @field_validator("evidence_type")
    @classmethod
    def validate_evidence_type(cls, value: str) -> str:
        if value not in EVIDENCE_TYPES:
            raise ValueError("invalid evidence type")
        return value

    @field_validator("relationship")
    @classmethod
    def validate_relationship(cls, value: str) -> str:
        if value not in EVIDENCE_RELATIONSHIPS:
            raise ValueError("invalid evidence relationship")
        return value

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        return _clean_optional(value)


class EvidenceUpdate(EvidenceCreate):
    pass


class EvidenceAssessmentUpdate(BaseModel):
    credibility_rating: str | None = None
    credibility_rationale: str | None = Field(default=None, max_length=4000)

    @field_validator("credibility_rating")
    @classmethod
    def validate_credibility_rating(cls, value: str | None) -> str | None:
        if value is not None and value not in ASSESSMENT_LEVELS:
            raise ValueError("invalid credibility rating")
        return value

    @field_validator("credibility_rationale")
    @classmethod
    def clean_credibility_rationale(cls, value: str | None) -> str | None:
        return _clean_optional(value)

    @model_validator(mode="after")
    def require_rationale_for_rating(self) -> "EvidenceAssessmentUpdate":
        if self.credibility_rating is not None and self.credibility_rationale is None:
            raise ValueError("credibility rationale is required when credibility is assessed")
        return self


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    claim_id: int
    source_title: str
    source_url: str
    evidence_type: str
    relationship: str
    notes: str | None
    credibility_rating: str | None
    credibility_rationale: str | None
    created_at: datetime
    updated_at: datetime


class ClaimValidationJudgmentCreate(BaseModel):
    validation_status: str
    confidence_level: str
    rationale: str = Field(min_length=1, max_length=4000)
    unresolved_questions: str | None = Field(default=None, max_length=4000)

    @field_validator("validation_status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALIDATION_STATUSES:
            raise ValueError("invalid validation status")
        return value

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence(cls, value: str) -> str:
        if value not in ASSESSMENT_LEVELS:
            raise ValueError("invalid confidence level")
        return value

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        return _required(value, "validation rationale")

    @field_validator("unresolved_questions")
    @classmethod
    def clean_unresolved_questions(cls, value: str | None) -> str | None:
        return _clean_optional(value)


class ClaimValidationJudgmentRead(BaseModel):
    id: int
    claim_id: int
    reviewer_id: int
    validation_status: str
    confidence_level: str
    rationale: str
    unresolved_questions: str | None
    reviewed_at: datetime
    is_stale: bool


class ClaimValidationSummary(BaseModel):
    claim_id: int
    confidence_level: str | None
    supporting_count: int
    contradicting_count: int
    neutral_count: int
    assessed_evidence_count: int
    total_evidence_count: int
    has_unresolved_contradiction: bool


class InvestigationValidationSummary(BaseModel):
    investigation_id: int
    claim_count: int
    assessed_claim_count: int
    low_confidence_count: int
    medium_confidence_count: int
    high_confidence_count: int
    unresolved_contradiction_count: int
    claims: list[ClaimValidationSummary]


class ResearchLearningRecommendation(BaseModel):
    competency: str
    lesson_slug: str
    lesson_title: str
    gap_type: str
    priority: int = Field(ge=1, le=5)
    reason: str


class InvestigationEducationRecommendations(BaseModel):
    investigation_id: int
    recommendation_count: int
    completion_authority: str
    recommendations: list[ResearchLearningRecommendation]
