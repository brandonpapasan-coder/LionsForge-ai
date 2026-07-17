from pydantic import BaseModel

from app.schemas.research_packet_comparison_report_chain_export_integrity import (
    IntegrityStatus,
    ResearchPacketComparisonChainVerificationIntegrityRequest,
)


class ResearchPacketComparisonChainVerificationIntegrityReceiptContent(BaseModel):
    schema_version: str = "1.0"
    report_type: str = (
        "research_packet_comparison_chain_verification_integrity_receipt"
    )
    integrity_status: IntegrityStatus
    supplied_sha256: str
    computed_sha256: str
    source_schema_version: str | None = None
    source_report_type: str | None = None
    detail: str
    disclaimer: str


class ResearchPacketComparisonChainVerificationIntegrityReceiptRequest(
    ResearchPacketComparisonChainVerificationIntegrityRequest
):
    pass


class ResearchPacketComparisonChainVerificationIntegrityReceiptResult(BaseModel):
    integrity_receipt_sha256: str
    content: ResearchPacketComparisonChainVerificationIntegrityReceiptContent
