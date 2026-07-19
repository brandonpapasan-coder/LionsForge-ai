from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


INVESTIGATION_STATUSES = {"open", "in_review", "validated", "archived"}


def _clean_required(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    research_question: str = Field(min_length=1, max_length=4000)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _clean_required(value, "title")

    @field_validator("research_question")
    @classmethod
    def validate_research_question(cls, value: str) -> str:
        return _clean_required(value, "research question")


class InvestigationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    research_question: str | None = Field(default=None, min_length=1, max_length=4000)
    status: str | None = None

    @field_validator("title")
    @classmethod
    def validate_optional_title(cls, value: str | None) -> str | None:
        return None if value is None else _clean_required(value, "title")

    @field_validator("research_question")
    @classmethod
    def validate_optional_research_question(cls, value: str | None) -> str | None:
        return None if value is None else _clean_required(value, "research question")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in INVESTIGATION_STATUSES:
            raise ValueError("invalid investigation status")
        return value


class InvestigationSynthesisUpdate(BaseModel):
    findings: str | None = Field(default=None, max_length=12000)
    limitations: str | None = Field(default=None, max_length=12000)
    unresolved_questions: str | None = Field(default=None, max_length=12000)

    @field_validator("findings", "limitations", "unresolved_questions")
    @classmethod
    def normalize_sections(cls, value: str | None) -> str | None:
        return _clean_optional(value)


class InvestigationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    research_question: str
    status: str
    findings: str | None
    limitations: str | None
    unresolved_questions: str | None
    created_at: datetime
    updated_at: datetime
