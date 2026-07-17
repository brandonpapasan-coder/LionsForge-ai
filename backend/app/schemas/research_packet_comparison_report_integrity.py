from typing import Any, Literal

from pydantic import BaseModel, Field


IntegrityStatus = Literal["matching", "changed", "unsupported"]


class ResearchPacketComparisonReportIntegrityRequest(BaseModel):
    report_sha256: str = Field(min_length=64, max_length=64)
    content: dict[str, Any]


class ResearchPacketComparisonReportIntegrityResult(BaseModel):
    status: IntegrityStatus
    supplied_sha256: str
    computed_sha256: str
    schema_version: str | None = None
    report_type: str | None = None
    supported_schema_versions: list[str] = Field(default_factory=lambda: ["1.0"])
    supported_report_types: list[str] = Field(
        default_factory=lambda: ["research_packet_comparison"]
    )
    detail: str
    disclaimer: str
