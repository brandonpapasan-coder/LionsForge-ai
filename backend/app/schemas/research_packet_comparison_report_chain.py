from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.research_packet_comparison_report import (
    ResearchPacketComparisonReportContent,
)


ChainStatus = Literal["consistent", "inconsistent", "unsupported"]


class ResearchPacketChainInput(BaseModel):
    content_sha256: str = Field(min_length=64, max_length=64)
    content: dict[str, Any]


class ResearchPacketComparisonReportChainInput(BaseModel):
    report_sha256: str = Field(min_length=64, max_length=64)
    content: ResearchPacketComparisonReportContent


class ResearchPacketComparisonReportChainRequest(BaseModel):
    left: ResearchPacketChainInput
    right: ResearchPacketChainInput
    report: ResearchPacketComparisonReportChainInput


class ResearchPacketComparisonReportChainResult(BaseModel):
    status: ChainStatus
    left_packet_hash_matches: bool
    right_packet_hash_matches: bool
    report_hash_matches: bool
    failed_checks: list[str] = Field(default_factory=list)
    detail: str
    disclaimer: str
