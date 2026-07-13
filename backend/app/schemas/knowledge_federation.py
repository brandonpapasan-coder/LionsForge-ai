from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FederationStatus = Literal["proposed", "accepted", "rejected", "archived"]
FederationLinkType = Literal[
    "duplicate",
    "supporting",
    "contradicting",
    "related",
    "superseding",
]


class KnowledgeFederationUpdate(BaseModel):
    link_type: FederationLinkType | None = None
    status: FederationStatus | None = None


class KnowledgeFederationRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    revision_number: int
    link_type: str
    score: float
    score_components: dict
    provenance: dict
    status: str
    created_at: datetime


class KnowledgeFederationLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_memory_id: int
    target_memory_id: int
    source_project_id: int
    target_project_id: int
    link_type: str
    score: float
    score_components: dict
    provenance: dict
    status: str
    fingerprint: str
    revision_number: int
    created_at: datetime
    updated_at: datetime
    revisions: list[KnowledgeFederationRevisionRead] = Field(default_factory=list)


class KnowledgeFederationScanResult(BaseModel):
    links: list[KnowledgeFederationLinkRead]
    created_count: int
    reused_count: int


class KnowledgeFederationSynthesis(BaseModel):
    total_links: int
    duplicates: list[KnowledgeFederationLinkRead]
    supporting: list[KnowledgeFederationLinkRead]
    contradicting: list[KnowledgeFederationLinkRead]
    related: list[KnowledgeFederationLinkRead]
    superseding: list[KnowledgeFederationLinkRead]
