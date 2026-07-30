"""Internal alpha operational metrics primitives."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AlphaMetrics:
    active_testers: int
    active_experiments: int
    feedback_items: int
    completed_experiments: int


def build_metrics(*, active_testers: int, active_experiments: int, feedback_items: int, completed_experiments: int) -> AlphaMetrics:
    values = [active_testers, active_experiments, feedback_items, completed_experiments]
    if any(value < 0 for value in values):
        raise ValueError("metrics cannot be negative")
    return AlphaMetrics(*values)
