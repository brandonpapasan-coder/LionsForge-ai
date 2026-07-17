import hashlib
import json

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.research_packet_comparison_report_chain_export_integrity_receipt_integrity import (
    ResearchPacketComparisonChainVerificationIntegrityReceiptIntegrityRequest,
    ResearchPacketComparisonChainVerificationIntegrityReceiptIntegrityResult,
)

router = APIRouter()
SUPPORTED_SCHEMA_VERSIONS = ["1.0"]
SUPPORTED_REPORT_TYPES = [
    "research_packet_comparison_chain_verification_integrity_receipt"
]
DISCLAIMER = (
    "This check compares integrity-receipt content represented by canonical JSON. "
    "It does not certify truth, quality, authorship, approval, or publication status."
)


def _canonical_sha256(content: dict[str, object]) -> str:
    payload = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@router.post(
    "/verify",
    response_model=ResearchPacketComparisonChainVerificationIntegrityReceiptIntegrityResult,
)
def verify_research_packet_comparison_chain_verification_integrity_receipt(
    request: ResearchPacketComparisonChainVerificationIntegrityReceiptIntegrityRequest,
    _current_user: User = Depends(get_current_user),
) -> ResearchPacketComparisonChainVerificationIntegrityReceiptIntegrityResult:
    schema_value = request.content.get("schema_version")
    report_type_value = request.content.get("report_type")
    schema_version = schema_value if isinstance(schema_value, str) else None
    report_type = report_type_value if isinstance(report_type_value, str) else None
    computed_sha256 = _canonical_sha256(request.content)

    unsupported = (
        schema_version not in SUPPORTED_SCHEMA_VERSIONS
        or report_type not in SUPPORTED_REPORT_TYPES
    )
    if unsupported:
        return ResearchPacketComparisonChainVerificationIntegrityReceiptIntegrityResult(
            status="unsupported",
            supplied_sha256=request.integrity_receipt_sha256,
            computed_sha256=computed_sha256,
            schema_version=schema_version,
            report_type=report_type,
            supported_schema_versions=SUPPORTED_SCHEMA_VERSIONS,
            supported_report_types=SUPPORTED_REPORT_TYPES,
            detail="The integrity receipt schema version or report type is unsupported.",
            disclaimer=DISCLAIMER,
        )

    matches = computed_sha256 == request.integrity_receipt_sha256.lower()
    return ResearchPacketComparisonChainVerificationIntegrityReceiptIntegrityResult(
        status="matching" if matches else "changed",
        supplied_sha256=request.integrity_receipt_sha256,
        computed_sha256=computed_sha256,
        schema_version=schema_version,
        report_type=report_type,
        supported_schema_versions=SUPPORTED_SCHEMA_VERSIONS,
        supported_report_types=SUPPORTED_REPORT_TYPES,
        detail=(
            "The integrity receipt content matches the supplied SHA-256 value."
            if matches
            else "The integrity receipt content does not match the supplied SHA-256 value."
        ),
        disclaimer=DISCLAIMER,
    )
