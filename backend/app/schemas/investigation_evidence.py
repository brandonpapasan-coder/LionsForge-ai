from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

EVIDENCE_TYPES = {"primary", "secondary", "dataset", "expert", "other"}
EVIDENCE_RELATIONSHIPS = {"supports", "contradicts", "neutral"}


def _required(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    return cleaned


class ClaimCreate(BaseModel):
    statement: str = Field(min_length=1, max_length=4000)

    @field_validator("statement")
    @classmethod
    def validate_statement(cls, value: str) -> str:
        return _required(value, "claim")


class ClaimUpdate(ClaimCreate):
    pass


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_id: int
    statement: str
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
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class EvidenceUpdate(EvidenceCreate):
    pass


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    claim_id: int
    source_title: str
    source_url: str
    evidence_type: str
    relationship: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
