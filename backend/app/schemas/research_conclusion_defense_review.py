from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DefenseReviewStatus = Literal["incomplete", "complete"]


class ResearchConclusionDefenseUpdate(BaseModel):
    evidence_coverage: str = Field(default="", max_length=10_000)
    strongest_counterargument: str = Field(default="", max_length=10_000)
    known_limitations: str = Field(default="", max_length=10_000)
    unresolved_questions: str = Field(default="", max_length=10_000)
    confidence_rationale: str = Field(default="", max_length=10_000)
    evidence_ids: list[int] = Field(default_factory=list, max_length=500)
    conclusion_revision_number: int | None = Field(default=None, ge=1)
    revision_note: str | None = Field(default=None, max_length=1_000)

    @field_validator("evidence_ids")
    @classmethod
    def deduplicate_evidence_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class ResearchConclusionDefenseRevision(BaseModel):
    id: int
    revision_number: int
    conclusion_revision_number: int | None
    evidence_ids: list[int]
    evidence_coverage: str
    strongest_counterargument: str
    known_limitations: str
    unresolved_questions: str
    confidence_rationale: str
    status: DefenseReviewStatus
    missing_sections: list[str]
    revision_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchConclusionDefenseWorkspace(BaseModel):
    id: int | None
    project_id: int
    conclusion_revision_number: int | None
    evidence_ids: list[int]
    evidence_coverage: str
    strongest_counterargument: str
    known_limitations: str
    unresolved_questions: str
    confidence_rationale: str
    status: DefenseReviewStatus
    missing_sections: list[str]
    revision_count: int
    created_at: datetime | None
    updated_at: datetime | None
    revisions: list[ResearchConclusionDefenseRevision]
    disclaimer: str
