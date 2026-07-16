from typing import Any, Literal

from pydantic import BaseModel, Field


IntegrityStatus = Literal["matching", "changed", "unsupported"]


class ResearchPacketIntegrityRequest(BaseModel):
    content_sha256: str = Field(min_length=64, max_length=64)
    content: dict[str, Any]


class ResearchPacketIntegrityResult(BaseModel):
    status: IntegrityStatus
    supplied_sha256: str
    computed_sha256: str
    schema_version: str | None = None
    supported_schema_versions: list[str] = Field(default_factory=lambda: ["1.0"])
    detail: str
    disclaimer: str
