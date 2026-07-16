import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.research_packet_comparison import (
    ResearchPacketComparisonRequest,
    ResearchPacketComparisonResult,
    ResearchPacketDifference,
)

router = APIRouter()
SUPPORTED_SCHEMA_VERSIONS = ["1.0"]
DISCLAIMER = (
    "This comparison identifies structural content differences only. It does not judge truth, quality, authorship, "
    "approval, or publication status."
)


def _canonical_sha256(content: dict[str, Any]) -> str:
    payload = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _join_path(parent: str, key: str) -> str:
    return f"{parent}.{key}" if parent else key


def _diff_values(left: Any, right: Any, path: str = "") -> list[ResearchPacketDifference]:
    if isinstance(left, dict) and isinstance(right, dict):
        differences: list[ResearchPacketDifference] = []
        for key in sorted(set(left) | set(right)):
            child_path = _join_path(path, str(key))
            if key not in left:
                differences.append(ResearchPacketDifference(path=child_path, kind="added"))
            elif key not in right:
                differences.append(ResearchPacketDifference(path=child_path, kind="removed"))
            else:
                differences.extend(_diff_values(left[key], right[key], child_path))
        return differences

    if isinstance(left, list) and isinstance(right, list):
        differences = []
        limit = max(len(left), len(right))
        for index in range(limit):
            child_path = f"{path}[{index}]" if path else f"[{index}]"
            if index >= len(left):
                differences.append(ResearchPacketDifference(path=child_path, kind="added"))
            elif index >= len(right):
                differences.append(ResearchPacketDifference(path=child_path, kind="removed"))
            else:
                differences.extend(_diff_values(left[index], right[index], child_path))
        return differences

    if left != right or type(left) is not type(right):
        return [ResearchPacketDifference(path=path or "$", kind="changed")]
    return []


@router.post("/compare", response_model=ResearchPacketComparisonResult)
def compare_research_packets(
    request: ResearchPacketComparisonRequest,
    _current_user: User = Depends(get_current_user),
) -> ResearchPacketComparisonResult:
    left_schema_value = request.left.content.get("schema_version")
    right_schema_value = request.right.content.get("schema_version")
    left_schema = left_schema_value if isinstance(left_schema_value, str) else None
    right_schema = right_schema_value if isinstance(right_schema_value, str) else None
    left_hash = _canonical_sha256(request.left.content)
    right_hash = _canonical_sha256(request.right.content)
    left_matches = left_hash == request.left.content_sha256.lower()
    right_matches = right_hash == request.right.content_sha256.lower()

    if left_schema not in SUPPORTED_SCHEMA_VERSIONS or right_schema not in SUPPORTED_SCHEMA_VERSIONS:
        return ResearchPacketComparisonResult(
            status="unsupported",
            left_computed_sha256=left_hash,
            right_computed_sha256=right_hash,
            left_hash_matches=left_matches,
            right_hash_matches=right_matches,
            left_schema_version=left_schema,
            right_schema_version=right_schema,
            supported_schema_versions=SUPPORTED_SCHEMA_VERSIONS,
            detail="One or both packet schema versions are not supported by this comparison workflow.",
            disclaimer=DISCLAIMER,
        )

    differences = _diff_values(request.left.content, request.right.content)
    added_count = sum(item.kind == "added" for item in differences)
    removed_count = sum(item.kind == "removed" for item in differences)
    changed_count = sum(item.kind == "changed" for item in differences)
    return ResearchPacketComparisonResult(
        status="identical" if not differences else "different",
        left_computed_sha256=left_hash,
        right_computed_sha256=right_hash,
        left_hash_matches=left_matches,
        right_hash_matches=right_matches,
        left_schema_version=left_schema,
        right_schema_version=right_schema,
        supported_schema_versions=SUPPORTED_SCHEMA_VERSIONS,
        differences=differences,
        added_count=added_count,
        removed_count=removed_count,
        changed_count=changed_count,
        detail=(
            "The packet content is structurally identical."
            if not differences
            else "The packet content contains structural differences."
        ),
        disclaimer=DISCLAIMER,
    )
