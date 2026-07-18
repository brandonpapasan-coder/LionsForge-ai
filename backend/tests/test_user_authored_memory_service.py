from types import SimpleNamespace

import pytest

from app.services.user_authored_memory_service import (
    contains_prohibited_secret,
    validate_user_authored_revision,
)


@pytest.mark.parametrize(
    "value",
    [
        "api_key=super-secret-value",
        "access token: abc123",
        "password=hunter2",
        "-----BEGIN PRIVATE KEY-----",
        "sk-proj_abcdefghijklmnopqrstuvwxyz",
    ],
)
def test_contains_prohibited_secret_rejects_credentials(value: str) -> None:
    assert contains_prohibited_secret(value)


@pytest.mark.parametrize(
    "value",
    [
        "I prefer primary sources and explicit uncertainty.",
        "My learning goal is to master causal inference.",
        "Review misconceptions before introducing advanced material.",
    ],
)
def test_contains_prohibited_secret_accepts_normal_memory(value: str) -> None:
    assert not contains_prohibited_secret(value)


def _memory(**overrides: object) -> SimpleNamespace:
    values = {
        "statement": "Prefer primary sources",
        "summary": "Primary source preference",
        "category": "research_preference",
        "status": "provisional",
        "confidence": 0.8,
        "source_evidence_ids": [],
        "provenance": {"origin": "user_authored"},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_revision_rejects_secret_in_updated_statement() -> None:
    with pytest.raises(ValueError, match="secret or credential"):
        validate_user_authored_revision(
            _memory(),
            {"statement": "api_key=super-secret-value"},
        )


def test_revision_rejects_manual_validation() -> None:
    with pytest.raises(ValueError, match="cannot be manually marked as validated"):
        validate_user_authored_revision(_memory(), {"status": "validated"})


def test_revision_requires_evidence_for_mastery_signal() -> None:
    with pytest.raises(ValueError, match="requires evidence IDs"):
        validate_user_authored_revision(
            _memory(category="mastery_signal"),
            {"source_evidence_ids": []},
        )


def test_revision_allows_safe_preference_edit() -> None:
    validate_user_authored_revision(
        _memory(),
        {"statement": "Prefer peer-reviewed primary sources"},
    )


def test_revision_does_not_restrict_research_generated_memory() -> None:
    validate_user_authored_revision(
        _memory(provenance={"origin": "mission_promotion"}),
        {"status": "validated"},
    )
