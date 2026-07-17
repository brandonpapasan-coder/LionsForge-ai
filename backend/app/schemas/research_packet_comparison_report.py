from typing import Any, Literal

from pydantic import BaseModel, Field


DifferenceKind = Literal["added", "removed", "changed"]
ReportStatus = Literal["identical", "different", "unsupported"]


class ResearchPacketReportInput(BaseModel):
    content_sha256: str = Field(min_length=64, max_length=64)
    content: dict[str, Any]


class ResearchPacketComparisonReportRequest(BaseModel):
    left: ResearchPacketReportInput
    right: ResearchPacketReportInput


class ResearchPacketReportDifference(BaseModel):
    path: str
    kind: DifferenceKind


class ResearchPacketComparisonReportContent(BaseModel):
    schema_version: str = "1.0"
    report_type: str = "research_packet_comparison"
    status: ReportStatus
    left_supplied_sha256: str
    left_computed_sha256: str
    left_hash_matches: bool
    right_supplied_sha256: str
    right_computed_sha256: str
    right_hash_matches: bool
    left_schema_version: str | None = None
    right_schema_version: str | None = None
    supported_schema_versions: list[str] = Field(default_factory=lambda: ["1.0"])
    added_count: int = 0
    removed_count: int = 0
    changed_count: int = 0
    differences: list[ResearchPacketReportDifference] = Field(default_factory=list)
    detail: str
    disclaimer: str


class ResearchPacketComparisonReportResult(BaseModel):
    report_sha256: str
    content: ResearchPacketComparisonReportContent
