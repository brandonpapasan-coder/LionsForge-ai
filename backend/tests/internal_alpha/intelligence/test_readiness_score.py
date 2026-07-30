import math

import pytest

from app.internal_alpha.intelligence.readiness_score import calculate_readiness_score


def test_marks_only_strong_balanced_scores_ready() -> None:
    result = calculate_readiness_score(
        security=95,
        reliability=92,
        feedback=90,
        regression=93,
    )
    assert result.overall == 92.5
    assert result.state == "READY"


def test_low_guardrail_score_keeps_candidate_not_ready() -> None:
    result = calculate_readiness_score(
        security=100,
        reliability=100,
        feedback=79,
        regression=100,
    )
    assert result.overall == 94.75
    assert result.state == "NOT_READY"


@pytest.mark.parametrize("value", [-1, 101, math.inf, math.nan])
def test_rejects_invalid_scores(value: float) -> None:
    with pytest.raises(ValueError):
        calculate_readiness_score(
            security=value,
            reliability=90,
            feedback=90,
            regression=90,
        )


def test_rejects_boolean_scores() -> None:
    with pytest.raises(TypeError):
        calculate_readiness_score(
            security=True,
            reliability=90,
            feedback=90,
            regression=90,
        )
