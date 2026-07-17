from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.routes.research_packet_comparison_report_chain_export_integrity import (
    _canonical_sha256,
    verify_research_packet_comparison_chain_verification_report,
)
from app.models.user import User
from app.schemas.research_packet_comparison_report_chain_export_integrity_receipt import (
    ResearchPacketComparisonChainVerificationIntegrityReceiptContent,
    ResearchPacketComparisonChainVerificationIntegrityReceiptRequest,
    ResearchPacketComparisonChainVerificationIntegrityReceiptResult,
)

router = APIRouter()


@router.post(
    "/export",
    response_model=ResearchPacketComparisonChainVerificationIntegrityReceiptResult,
)
def export_research_packet_comparison_chain_verification_integrity_receipt(
    request: ResearchPacketComparisonChainVerificationIntegrityReceiptRequest,
    current_user: User = Depends(get_current_user),
) -> ResearchPacketComparisonChainVerificationIntegrityReceiptResult:
    integrity = verify_research_packet_comparison_chain_verification_report(
        request=request,
        _current_user=current_user,
    )

    content = ResearchPacketComparisonChainVerificationIntegrityReceiptContent(
        integrity_status=integrity.status,
        supplied_sha256=integrity.supplied_sha256,
        computed_sha256=integrity.computed_sha256,
        source_schema_version=integrity.schema_version,
        source_report_type=integrity.report_type,
        detail=integrity.detail,
        disclaimer=integrity.disclaimer,
    )

    return ResearchPacketComparisonChainVerificationIntegrityReceiptResult(
        integrity_receipt_sha256=_canonical_sha256(content.model_dump()),
        content=content,
    )
