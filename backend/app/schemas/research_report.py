from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.evidence import EvidenceItem


class ResearchReportRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16, examples=["AAPL"])
    include_portfolio_context: bool = True
    persist: bool = True


class ResearchReportSection(BaseModel):
    title: str
    summary: str
    bullets: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ResearchReportMetadata(BaseModel):
    report_id: str
    symbol: str
    version: int
    status: str
    confidence_level: str
    confidence_score: Decimal = Field(ge=0, le=1)
    template_version: str
    model_version: str
    data_snapshot_id: str
    generated_at: datetime
    processing_duration_ms: float


class ResearchReport(BaseModel):
    metadata: ResearchReportMetadata
    title: str
    executive_summary: str
    sections: list[ResearchReportSection]
    bull_case: list[str]
    bear_case: list[str]
    risks: list[str]
    opportunities: list[str]
    evidence: list[EvidenceItem]
    data_quality_flags: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class ResearchReportRead(BaseModel):
    id: int
    report_id: str
    user_id: int
    symbol: str
    version: int
    title: str
    status: str
    confidence_level: str
    confidence_score: Decimal
    template_version: str
    model_version: str
    data_snapshot_id: str
    executive_summary: str
    report_payload: dict[str, Any]
    evidence_payload: list[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchReportList(BaseModel):
    symbol: str | None = None
    reports: list[ResearchReportRead]
