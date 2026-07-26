from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PracticumTemplateStatus = Literal["active", "retired"]
PracticumEnrollmentStatus = Literal[
    "not_started",
    "in_progress",
    "review_ready",
    "revision_required",
    "completed",
]
PracticumObjectiveStatus = Literal["missing_requirements", "ready_for_review", "approved"]
PracticumReviewDecisionValue = Literal["approved", "revision_required"]


class PracticumObjectiveRead(BaseModel):
    objective_key: str
    sequence: int
    title: str
    description: str
    competency: str
    required_evidence_categories: list[str]
    minimum_evidence_count: int
    reflection_required: bool
    human_review_required: bool


class PracticumTemplateRead(BaseModel):
    id: int
    slug: str
    version: int
    title: str
    description: str
    estimated_minutes: int
    prerequisite_lesson_slugs: list[str]
    status: PracticumTemplateStatus
    objectives: list[PracticumObjectiveRead]


class PracticumEnrollmentCreate(BaseModel):
    template_slug: str = Field(min_length=1, max_length=120)
    research_project_id: int = Field(gt=0)


class PracticumObjectiveProgressUpdate(BaseModel):
    reflection: str | None = Field(default=None, max_length=12000)


class PracticumEvidenceReferenceCreate(BaseModel):
    research_evidence_id: int = Field(gt=0)


class PracticumEvidenceReferenceRead(BaseModel):
    id: int
    research_evidence_id: int
    created_at: datetime


class PracticumObjectiveProgressRead(BaseModel):
    objective_key: str
    reflection: str | None
    reflection_source: Literal["learner_authored"] = "learner_authored"
    evidence_references: list[PracticumEvidenceReferenceRead]
    created_at: datetime
    updated_at: datetime


class PracticumReviewDecisionCreate(BaseModel):
    decision: PracticumReviewDecisionValue
    notes: str | None = Field(default=None, max_length=12000)


class PracticumReviewDecisionRead(BaseModel):
    id: int
    reviewer_user_id: int
    decision: PracticumReviewDecisionValue
    notes: str | None
    decision_source: Literal["human_reviewer"] = "human_reviewer"
    created_at: datetime


class PracticumObjectiveReadinessRead(BaseModel):
    objective_key: str
    sequence: int
    competency: str
    status: PracticumObjectiveStatus
    referenced_evidence_ids: list[int]
    covered_evidence_categories: list[str]
    reflection_present: bool
    human_review_required: bool
    missing_requirements: list[str]


class PracticumReadinessRead(BaseModel):
    enrollment_id: int
    enrollment_status: PracticumEnrollmentStatus
    system_evaluation_source: Literal["deterministic_rules"] = "deterministic_rules"
    advisory_notice: str
    objectives: list[PracticumObjectiveReadinessRead]
    missing_requirements: list[str]
    ready_for_human_review: bool
    latest_review_decision: PracticumReviewDecisionRead | None


class PracticumEnrollmentRead(BaseModel):
    id: int
    user_id: int
    template_slug: str
    template_version: int
    research_project_id: int
    status: PracticumEnrollmentStatus
    started_at: datetime | None
    submitted_for_review_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    objectives: list[PracticumObjectiveProgressRead]
    review_history: list[PracticumReviewDecisionRead]
