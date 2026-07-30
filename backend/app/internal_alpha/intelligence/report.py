"""Aggregate privacy-safe internal-alpha intelligence report."""

from dataclasses import dataclass

from .dashboard_metrics import AlphaMetrics
from .readiness_score import ReadinessScore


@dataclass(frozen=True)
class AlphaIntelligenceReport:
    candidate_sha: str
    metrics: AlphaMetrics
    readiness: ReadinessScore
    repeated_categories: tuple[tuple[str, int], ...]
    blocking_reasons: tuple[str, ...]


def build_intelligence_report(
    *,
    candidate_sha: str,
    metrics: AlphaMetrics,
    readiness: ReadinessScore,
    repeated_categories: dict[str, int],
) -> AlphaIntelligenceReport:
    """Build a deterministic report without tester identity or free-form feedback."""
    if len(candidate_sha) != 40 or any(char not in "0123456789abcdef" for char in candidate_sha):
        raise ValueError("candidate_sha must be a lowercase 40-character hexadecimal SHA")
    if any(count < 2 for count in repeated_categories.values()):
        raise ValueError("repeated category counts must be at least two")

    repeated = tuple(sorted(repeated_categories.items(), key=lambda item: (-item[1], item[0])))
    blocking: list[str] = []
    if readiness.state != "READY":
        blocking.append("READINESS_GUARDRAIL_NOT_MET")
    if metrics.active_experiments == 0:
        blocking.append("NO_ACTIVE_EXPERIMENTS")
    if metrics.feedback_items == 0:
        blocking.append("NO_FEEDBACK_EVIDENCE")
    if repeated_categories.get("DEFECT", 0) >= 2:
        blocking.append("REPEATED_DEFECT_SIGNAL")

    return AlphaIntelligenceReport(
        candidate_sha=candidate_sha,
        metrics=metrics,
        readiness=readiness,
        repeated_categories=repeated,
        blocking_reasons=tuple(sorted(blocking)),
    )
