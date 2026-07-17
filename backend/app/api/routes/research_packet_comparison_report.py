import hashlib
import json

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.routes.research_packet_comparison import (
    SUPPORTED_SCHEMA_VERSIONS,
    _canonical_sha256,
    _diff_values,
)
from app.models.user import User
from app.schemas.research_packet_comparison_report import (
    ResearchPacketComparisonReportContent,
    ResearchPacketComparisonReportRequest,
    ResearchPacketComparisonReportResult,
    ResearchPacketReportDifference,
)

router = APIRouter()
DISCLAIMER = (
    "This report records structural content differences only. It does not judge or "
    "certify truth, quality, authorship, approval, or publication status."
)


def _report_sha256(content: ResearchPacketComparisonReportContent) -> str:
    payload = json.dumps(
        content.model_dump(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@router.post("/export", response_model=ResearchPacketComparisonReportResult)
def export_research_packet_comparison_report(
    request: ResearchPacketComparisonReportRequest,
    _current_user: User = Depends(get_current_user),
) -> ResearchPacketComparisonReportResult:
    left_schema_value = request.left.content.get("schema_version")
    right_schema_value = request.right.content.get("schema_version")
    left_schema = left_schema_value if isinstance(left_schema_value, str) else None
    right_schema = right_schema_value if isinstance(right_schema_value, str) else None
    left_hash = _canonical_sha256(request.left.content)
    right_hash = _canonical_sha256(request.right.content)
    left_matches = left_hash == request.left.content_sha256.lower()
    right_matches = right_hash == request.right.content_sha256.lower()

    unsupported = (
        left_schema not in SUPPORTED_SCHEMA_VERSIONS
        or right_schema not in SUPPORTED_SCHEMA_VERSIONS
    )
    differences = (
        []
        if unsupported
        else _diff_values(request.left.content, request.right.content)
    )
    report_differences = [
        ResearchPacketReportDifference(path=item.path, kind=item.kind)
        for item in differences
    ]
    added_count = sum(item.kind == "added" for item in report_differences)
    removed_count = sum(item.kind == "removed" for item in report_differences)
    changed_count = sum(item.kind == "changed" for item in report_differences)

    status = (
        "unsupported"
        if unsupported
        else ("identical" if not report_differences else "different")
    )
    detail = (
        "One or both packet schema versions are unsupported."
        if unsupported
        else (
            "The packet content is structurally identical."
            if not report_differences
            else "The packet content contains structural differences."
        )
    )
    content = ResearchPacketComparisonReportContent(
        status=status,
        left_supplied_sha256=request.left.content_sha256,
        left_computed_sha256=left_hash,
        left_hash_matches=left_matches,
        right_supplied_sha256=request.right.content_sha256,
        right_computed_sha256=right_hash,
        right_hash_matches=right_matches,
        left_schema_version=left_schema,
        right_schema_version=right_schema,
        supported_schema_versions=SUPPORTED_SCHEMA_VERSIONS,
        added_count=added_count,
        removed_count=removed_count,
        changed_count=changed_count,
        differences=report_differences,
        detail=detail,
        disclaimer=DISCLAIMER,
    )
    return ResearchPacketComparisonReportResult(
        report_sha256=_report_sha256(content),
        content=content,
    )
