from typing import Any, Literal

from pydantic import BaseModel, Field


ComparisonStatus = Literal["identical", "different", "unsupported"]
DifferenceKind = Literal["added", "removed", "changed"]


class ResearchPacketInput(BaseModel):
    content_sha256: str = Field(min_length=64, max_length=64)
    content: dict[str, Any]


class ResearchPacketComparisonRequest(BaseModel):
    left: ResearchPacketInput
    right: ResearchPacketInput


class ResearchPacketDifference(BaseModel):
    path: str
    kind: DifferenceKind


class ResearchPacketComparisonResult(BaseModel):
    status: ComparisonStatus
    left_computed_sha256: str
    right_computed_sha256: str
    left_hash_matches: bool
    right_hash_matches: bool
    left_schema_version: str | None = None
    right_schema_version: str | None = None
    supported_schema_versions: list[str] = Field(default_factory=lambda: ["1.0"])
    differences: list[ResearchPacketDifference] = Field(default_factory=list)
    added_count: int = 0
    removed_count: int = 0
    changed_count: int = 0
    detail: str
    disclaimer: str
