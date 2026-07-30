"""Deterministic internal-alpha operational metrics.

The metrics layer accepts only bounded non-negative integers and emits no tester-level
or free-form data.
"""

from dataclasses import dataclass


_MAX_METRIC = 1_000_000


@dataclass(frozen=True)
class AlphaMetrics:
    active_testers: int
    active_experiments: int
    feedback_items: int
    completed_experiments: int


def _validate_count(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not 0 <= value <= _MAX_METRIC:
        raise ValueError(f"{name} must be between 0 and {_MAX_METRIC}")


def build_metrics(
    *,
    active_testers: int,
    active_experiments: int,
    feedback_items: int,
    completed_experiments: int,
) -> AlphaMetrics:
    values = {
        "active_testers": active_testers,
        "active_experiments": active_experiments,
        "feedback_items": feedback_items,
        "completed_experiments": completed_experiments,
    }
    for name, value in values.items():
        _validate_count(name, value)
    return AlphaMetrics(**values)
