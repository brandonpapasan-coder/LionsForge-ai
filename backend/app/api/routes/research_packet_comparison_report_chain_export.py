import hashlib
import json

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.routes.research_packet_comparison import _canonical_sha256
from app.api.routes.research_packet_comparison_report_chain import (
    _report_sha256,
    verify_research_packet_comparison_report_chain,
)
from app.models.user import User
from app.schemas.research_packet_comparison_report_chain_export import (
    ResearchPacketComparisonChainVerificationContent,
    ResearchPacketComparisonChainVerificationExportRequest,
    ResearchPacketComparisonChainVerificationExportResult,
)

router = APIRouter()


def _verification_report_sha256(
    content: ResearchPacketComparisonChainVerificationContent,
) -> str:
    payload = json.dumps(
        content.model_dump(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@router.post(
    "/export",
    response_model=ResearchPacketComparisonChainVerificationExportResult,
)
def export_research_packet_comparison_chain_verification_report(
    request: ResearchPacketComparisonChainVerificationExportRequest,
    current_user: User = Depends(get_current_user),
) -> ResearchPacketComparisonChainVerificationExportResult:
    verification = verify_research_packet_comparison_report_chain(
        request=request,
        _current_user=current_user,
    )
    left_schema_value = request.left.content.get("schema_version")
    right_schema_value = request.right.content.get("schema_version")
    left_schema = left_schema_value if isinstance(left_schema_value, str) else None
    right_schema = right_schema_value if isinstance(right_schema_value, str) else None
    left_computed = _canonical_sha256(request.left.content)
    right_computed = _canonical_sha256(request.right.content)
    comparison_report_content = request.report.content.model_dump()
    comparison_report_computed = _report_sha256(comparison_report_content)

    content = ResearchPacketComparisonChainVerificationContent(
        chain_status=verification.status,
        left_supplied_sha256=request.left.content_sha256,
        left_computed_sha256=left_computed,
        left_hash_matches=verification.left_packet_hash_matches,
        right_supplied_sha256=request.right.content_sha256,
        right_computed_sha256=right_computed,
        right_hash_matches=verification.right_packet_hash_matches,
        comparison_report_supplied_sha256=request.report.report_sha256,
        comparison_report_computed_sha256=comparison_report_computed,
        comparison_report_hash_matches=verification.report_hash_matches,
        left_schema_version=left_schema,
        right_schema_version=right_schema,
        comparison_report_schema_version=request.report.content.schema_version,
        comparison_report_type=request.report.content.report_type,
        failed_checks=verification.failed_checks,
        detail=verification.detail,
        disclaimer=verification.disclaimer,
    )
    return ResearchPacketComparisonChainVerificationExportResult(
        verification_report_sha256=_verification_report_sha256(content),
        content=content,
    )
