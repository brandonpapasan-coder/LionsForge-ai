import math

import pytest

from app.internal_alpha.intelligence.trend_detection import TrendPoint, detect_trend


def test_detects_up_down_and_flat_trends() -> None:
    assert detect_trend((TrendPoint("p1", 10), TrendPoint("p2", 15))).direction == "UP"
    assert detect_trend((TrendPoint("p1", 10), TrendPoint("p2", 5))).direction == "DOWN"
    result = detect_trend(
        (TrendPoint("p1", 10), TrendPoint("p2", 10.4)), flat_tolerance=0.5
    )
    assert result.direction == "FLAT"
    assert result.percentage_change == 4.0


def test_zero_baseline_has_no_percentage_change() -> None:
    result = detect_trend((TrendPoint("p1", 0), TrendPoint("p2", 5)))
    assert result.delta == 5
    assert result.percentage_change is None


def test_rejects_unbounded_duplicate_and_nonfinite_input() -> None:
    with pytest.raises(ValueError):
        detect_trend((TrendPoint("p1", 1),))
    with pytest.raises(ValueError):
        detect_trend((TrendPoint("p1", 1), TrendPoint("p1", 2)))
    with pytest.raises(ValueError):
        detect_trend((TrendPoint("p1", 1), TrendPoint("p2", math.inf)))
    with pytest.raises(ValueError):
        detect_trend((TrendPoint("p1", 1), TrendPoint("p2", 2)), flat_tolerance=-1)
