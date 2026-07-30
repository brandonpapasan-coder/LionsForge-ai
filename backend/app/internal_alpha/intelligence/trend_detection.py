"""Deterministic trend detection for bounded internal-alpha signals."""

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class TrendPoint:
    period: str
    value: float


@dataclass(frozen=True)
class TrendResult:
    direction: str
    delta: float
    percentage_change: float | None


VALID_DIRECTIONS = {"UP", "DOWN", "FLAT"}


def detect_trend(points: Iterable[TrendPoint], *, flat_tolerance: float = 0.0) -> TrendResult:
    """Compare the first and last bounded points without inferring causality."""
    series = tuple(points)
    if not 2 <= len(series) <= 365:
        raise ValueError("trend analysis requires between 2 and 365 points")
    if not isfinite(flat_tolerance) or flat_tolerance < 0:
        raise ValueError("flat_tolerance must be finite and non-negative")
    if len({point.period for point in series}) != len(series):
        raise ValueError("trend periods must be unique")
    if any(not point.period or len(point.period) > 64 for point in series):
        raise ValueError("trend periods must be bounded non-empty identifiers")
    if any(not isfinite(point.value) for point in series):
        raise ValueError("trend values must be finite")

    start = series[0].value
    end = series[-1].value
    delta = end - start
    if abs(delta) <= flat_tolerance:
        direction = "FLAT"
    elif delta > 0:
        direction = "UP"
    else:
        direction = "DOWN"

    percentage_change = None if start == 0 else round((delta / abs(start)) * 100, 2)
    return TrendResult(direction=direction, delta=round(delta, 4), percentage_change=percentage_change)
