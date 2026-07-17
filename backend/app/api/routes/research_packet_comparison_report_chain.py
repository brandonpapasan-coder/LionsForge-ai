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
from app.schemas.research_packet_comparison_report_chain import (
    ResearchPacketComparisonReportChainRequest,
    ResearchPacketComparisonReportChainResult,
)

router = APIRouter()
SUPPORTED_REPORT_TYPES = ["research_packet_comparison"]
DISCLAIMER = (
    "This verification checks deterministic integrity and consistency only. It does "
    "not certify truth, quality, authorship, approval, or publication status."
)


def _report_sha256(content: dict[str, object]) -> str:
    payload = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@router.post("/verify", response_model=ResearchPacketComparisonReportChainResult)
def verify_research_packet_comparison_report_chain(
    request: ResearchPacketComparisonReportChainRequest,
    _current_user: User = Depends(get_current_user),
) -> ResearchPacketComparisonReportChainResult:
    left_schema_value = request.left.content.get("schema_version")
    right_schema_value = request.right.content.get("schema_version")
    left_schema = left_schema_value if isinstance(left_schema_value, str) else None
    right_schema = right_schema_value if isinstance(right_schema_value, str) else None
    report_content = request.report.content.model_dump()

    unsupported = (
        left_schema not in SUPPORTED_SCHEMA_VERSIONS
        or right_schema not in SUPPORTED_SCHEMA_VERSIONS
        or request.report.content.schema_version not in SUPPORTED_SCHEMA_VERSIONS
        or request.report.content.report_type not in SUPPORTED_REPORT_TYPES
    )

    left_hash = _canonical_sha256(request.left.content)
    right_hash = _canonical_sha256(request.right.content)
    report_hash = _report_sha256(report_content)
    left_matches = left_hash == request.left.content_sha256.lower()
    right_matches = right_hash == request.right.content_sha256.lower()
    report_matches = report_hash == request.report.report_sha256.lower()

    if unsupported:
        return ResearchPacketComparisonReportChainResult(
            status="unsupported",
            left_packet_hash_matches=left_matches,
            right_packet_hash_matches=right_matches,
            report_hash_matches=report_matches,
            failed_checks=["supported_schema_and_report_type"],
            detail="One or more packet or report schema values are unsupported.",
            disclaimer=DISCLAIMER,
        )

    differences = _diff_values(request.left.content, request.right.content)
    expected_differences = [
        {"path": item.path, "kind": item.kind} for item in differences
    ]
    expected_added = sum(item.kind == "added" for item in differences)
    expected_removed = sum(item.kind == "removed" for item in differences)
    expected_changed = sum(item.kind == "changed" for item in differences)
    expected_status = "identical" if not differences else "different"
    report = request.report.content

    checks = {
        "left_packet_hash": left_matches,
        "right_packet_hash": right_matches,
        "report_hash": report_matches,
        "report_left_supplied_hash": (
            report.left_supplied_sha256.lower()
            == request.left.content_sha256.lower()
        ),
        "report_left_computed_hash": report.left_computed_sha256.lower() == left_hash,
        "report_left_hash_flag": report.left_hash_matches == left_matches,
        "report_right_supplied_hash": (
            report.right_supplied_sha256.lower()
            == request.right.content_sha256.lower()
        ),
        "report_right_computed_hash": report.right_computed_sha256.lower() == right_hash,
        "report_right_hash_flag": report.right_hash_matches == right_matches,
        "report_packet_schema_versions": (
            report.left_schema_version == left_schema
            and report.right_schema_version == right_schema
        ),
        "report_status": report.status == expected_status,
        "report_differences": (
            [item.model_dump() for item in report.differences]
            == expected_differences
        ),
        "report_difference_counts": (
            report.added_count == expected_added
            and report.removed_count == expected_removed
            and report.changed_count == expected_changed
        ),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    consistent = not failed_checks

    return ResearchPacketComparisonReportChainResult(
        status="consistent" if consistent else "inconsistent",
        left_packet_hash_matches=left_matches,
        right_packet_hash_matches=right_matches,
        report_hash_matches=report_matches,
        failed_checks=failed_checks,
        detail=(
            "The packets and comparison report form a consistent integrity chain."
            if consistent
            else "The packets and comparison report do not form a consistent integrity chain."
        ),
        disclaimer=DISCLAIMER,
    )
