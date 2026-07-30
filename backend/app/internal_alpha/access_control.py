"""Internal alpha access control validation foundation."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AlphaAccessGrant:
    tester_id: str
    candidate_sha: str
    environment: str
    expires_at: datetime
    approved: bool


ALLOWED_ENVIRONMENTS = {"INTERNAL_ALPHA"}


def validate_access(grant: AlphaAccessGrant) -> bool:
    return (
        bool(grant.tester_id)
        and bool(grant.candidate_sha)
        and grant.environment in ALLOWED_ENVIRONMENTS
        and grant.approved
        and grant.expires_at > datetime.utcnow()
    )
