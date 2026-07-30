"""Privacy-safe internal alpha feedback pipeline foundation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AlphaFeedback:
    feedback_id: str
    experiment_id: str
    severity: str
    category: str
    reproducible: bool


VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def validate_feedback(feedback: AlphaFeedback) -> bool:
    return (
        bool(feedback.feedback_id)
        and bool(feedback.experiment_id)
        and feedback.severity in VALID_SEVERITIES
        and bool(feedback.category)
    )
