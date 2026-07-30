"""Validation Agent foundation for research quality checks."""

from dataclasses import dataclass


@dataclass
class ValidationResult:
    confidence: str
    requires_review: bool
    findings: list[str]


class ValidationAgent:
    name = "validation_agent"

    def validate(self, claim: str) -> ValidationResult:
        return ValidationResult(
            confidence="unknown",
            requires_review=True,
            findings=[claim],
        )
