import hashlib
import json

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.research_packet_integrity import ResearchPacketIntegrityRequest, ResearchPacketIntegrityResult

router = APIRouter()
SUPPORTED_SCHEMA_VERSIONS = ["1.0"]
DISCLAIMER = (
    "This check compares packet bytes represented by canonical JSON. It does not certify truth, quality, authorship, "
    "approval, or publication status."
)


def _canonical_sha256(content: dict[str, object]) -> str:
    payload = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@router.post("/verify", response_model=ResearchPacketIntegrityResult)
def verify_research_packet(
    request: ResearchPacketIntegrityRequest,
    _current_user: User = Depends(get_current_user),
) -> ResearchPacketIntegrityResult:
    schema_version_value = request.content.get("schema_version")
    schema_version = schema_version_value if isinstance(schema_version_value, str) else None
    computed_sha256 = _canonical_sha256(request.content)

    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        return ResearchPacketIntegrityResult(
            status="unsupported",
            supplied_sha256=request.content_sha256,
            computed_sha256=computed_sha256,
            schema_version=schema_version,
            supported_schema_versions=SUPPORTED_SCHEMA_VERSIONS,
            detail="The packet schema version is not supported by this checker.",
            disclaimer=DISCLAIMER,
        )

    matches = computed_sha256 == request.content_sha256.lower()
    return ResearchPacketIntegrityResult(
        status="matching" if matches else "changed",
        supplied_sha256=request.content_sha256,
        computed_sha256=computed_sha256,
        schema_version=schema_version,
        supported_schema_versions=SUPPORTED_SCHEMA_VERSIONS,
        detail=(
            "The packet content matches the supplied SHA-256 value."
            if matches
            else "The packet content does not match the supplied SHA-256 value."
        ),
        disclaimer=DISCLAIMER,
    )
