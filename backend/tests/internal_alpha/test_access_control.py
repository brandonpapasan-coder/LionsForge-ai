from datetime import datetime, timedelta, timezone

from app.internal_alpha.access_control import AlphaAccessGrant, validate_access


NOW = datetime(2026, 7, 30, 20, 0, tzinfo=timezone.utc)
CANDIDATE = "a" * 40


def build(**changes: object) -> AlphaAccessGrant:
    values = {
        "tester_id": "tester_0001",
        "candidate_sha": CANDIDATE,
        "environment": "INTERNAL_ALPHA",
        "expires_at": NOW + timedelta(hours=1),
        "approved": True,
    }
    values.update(changes)
    return AlphaAccessGrant(**values)


def test_valid_grant_is_candidate_bound_and_active() -> None:
    assert validate_access(build(), now=NOW)


def test_rejects_unapproved_expired_or_wrong_environment() -> None:
    assert not validate_access(build(approved=False), now=NOW)
    assert not validate_access(build(expires_at=NOW), now=NOW)
    assert not validate_access(build(environment="PRODUCTION"), now=NOW)


def test_rejects_malformed_tester_and_candidate_identifiers() -> None:
    assert not validate_access(build(tester_id="person@example.com"), now=NOW)
    assert not validate_access(build(candidate_sha="abc123"), now=NOW)


def test_supports_naive_utc_expiry_without_crashing() -> None:
    naive_expiry = (NOW + timedelta(hours=1)).replace(tzinfo=None)
    assert validate_access(build(expires_at=naive_expiry), now=NOW)
