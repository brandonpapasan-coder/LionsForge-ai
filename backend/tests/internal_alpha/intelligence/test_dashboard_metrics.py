import pytest

from app.internal_alpha.intelligence.dashboard_metrics import AlphaMetrics, build_metrics


def test_builds_privacy_safe_metrics() -> None:
    assert build_metrics(
        active_testers=4,
        active_experiments=2,
        feedback_items=11,
        completed_experiments=3,
    ) == AlphaMetrics(4, 2, 11, 3)


@pytest.mark.parametrize("value", [-1, 1_000_001])
def test_rejects_out_of_bounds_counts(value: int) -> None:
    with pytest.raises(ValueError):
        build_metrics(
            active_testers=value,
            active_experiments=0,
            feedback_items=0,
            completed_experiments=0,
        )


def test_rejects_boolean_counts() -> None:
    with pytest.raises(TypeError):
        build_metrics(
            active_testers=True,
            active_experiments=0,
            feedback_items=0,
            completed_experiments=0,
        )
