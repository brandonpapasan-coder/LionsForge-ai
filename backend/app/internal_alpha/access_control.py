"""Internal alpha access-control validation.

Access grants are intentionally narrow: approved pseudonymous testers may access one
exact candidate only in the isolated internal-alpha environment and only while the
grant remains active.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import re


_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_TESTER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")


@dataclass(frozen=True)
class AlphaAccessGrant:
    tester_id: str
    candidate_sha: str
    environment: str
    expires_at: datetime
    approved: bool


ALLOWED_ENVIRONMENTS = {"INTERNAL_ALPHA"}


def validate_access(grant: AlphaAccessGrant, *, now: datetime | None = None) -> bool:
    """Return whether a grant satisfies the fail-closed internal-alpha boundary."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    expiry = grant.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    return (
        bool(_TESTER_ID.fullmatch(grant.tester_id))
        and bool(_SHA40.fullmatch(grant.candidate_sha))
        and grant.environment in ALLOWED_ENVIRONMENTS
        and grant.approved
        and expiry > current
    )
