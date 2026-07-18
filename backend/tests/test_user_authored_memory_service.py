import pytest

from app.services.user_authored_memory_service import contains_prohibited_secret


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
