"""Validation helpers for internal alpha control records."""


def validate_candidate_binding(candidate_sha: str, expected_sha: str) -> bool:
    return bool(candidate_sha) and candidate_sha == expected_sha


def validate_internal_environment(environment: str) -> bool:
    return environment == "internal-alpha"
