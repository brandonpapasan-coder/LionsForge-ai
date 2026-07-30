"""Deterministic internal-alpha readiness scoring primitives."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ReadinessScore:
    security: float
    reliability: float
    feedback: float
    regression: float
    overall: float
    state: str


def _validate_score(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    normalized = float(value)
    if not isfinite(normalized) or not 0 <= normalized <= 100:
        raise ValueError(f"{name} must be finite and between 0 and 100")
    return normalized


def calculate_readiness_score(
    *, security: float, reliability: float, feedback: float, regression: float
) -> ReadinessScore:
    scores = {
        "security": _validate_score("security", security),
        "reliability": _validate_score("reliability", reliability),
        "feedback": _validate_score("feedback", feedback),
        "regression": _validate_score("regression", regression),
    }
    overall = round(sum(scores.values()) / len(scores), 2)
    state = "READY" if overall >= 90 and min(scores.values()) >= 80 else "NOT_READY"
    return ReadinessScore(**scores, overall=overall, state=state)
