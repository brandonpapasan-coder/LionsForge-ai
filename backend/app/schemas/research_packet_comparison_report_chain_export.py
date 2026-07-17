from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.research_packet_comparison_report_chain import (
    ChainStatus,
    ResearchPacketComparisonReportChainRequest,
)


class ResearchPacketComparisonChainVerificationContent(BaseModel):
    schema_version: str = "1.0"
    report_type: str = "research_packet_comparison_chain_verification"
    chain_status: ChainStatus
    left_supplied_sha256: str
    left_computed_sha256: str
    left_hash_matches: bool
    right_supplied_sha256: str
    right_computed_sha256: str
    right_hash_matches: bool
    comparison_report_supplied_sha256: str
    comparison_report_computed_sha256: str
    comparison_report_hash_matches: bool
    left_schema_version: str | None = None
    right_schema_version: str | None = None
    comparison_report_schema_version: str | None = None
    comparison_report_type: str | None = None
    failed_checks: list[str] = Field(default_factory=list)
    detail: str
    disclaimer: str


class ResearchPacketComparisonChainVerificationExportRequest(
    ResearchPacketComparisonReportChainRequest
):
    pass


class ResearchPacketComparisonChainVerificationExportResult(BaseModel):
    verification_report_sha256: str
    content: ResearchPacketComparisonChainVerificationContent
