"""Privacy-safe internal-alpha feedback validation."""

from dataclasses import dataclass
from re import fullmatch


_ID = r"^[a-z0-9][a-z0-9_-]{7,63}$"
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_CATEGORIES = {"DEFECT", "USABILITY", "RESEARCH_QUALITY", "PERFORMANCE", "ACCESSIBILITY"}
VALID_REPRODUCIBILITY = {"ALWAYS", "INTERMITTENT", "ONCE", "NOT_APPLICABLE"}


@dataclass(frozen=True)
class AlphaFeedback:
    feedback_id: str
    experiment_id: str
    severity: str
    category: str
    reproducibility: str
    reason_codes: tuple[str, ...]


def validate_feedback(feedback: AlphaFeedback) -> bool:
    """Validate bounded, structured feedback without free-form or personal data."""
    if not fullmatch(_ID, feedback.feedback_id):
        return False
    if not fullmatch(_ID, feedback.experiment_id):
        return False
    if feedback.severity not in VALID_SEVERITIES:
        return False
    if feedback.category not in VALID_CATEGORIES:
        return False
    if feedback.reproducibility not in VALID_REPRODUCIBILITY:
        return False
    if not 1 <= len(feedback.reason_codes) <= 10:
        return False
    if len(set(feedback.reason_codes)) != len(feedback.reason_codes):
        return False
    if any(not fullmatch(_ID, code) for code in feedback.reason_codes):
        return False
    if feedback.category != "DEFECT" and feedback.severity == "CRITICAL":
        return False
    return True
