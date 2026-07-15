from decimal import Decimal

import pytest

from app.services.market_scenario import SCENARIOS, run_scenario


def test_scenario_replay_is_deterministic() -> None:
    first = run_scenario(
        scenario_name="bull_market",
        initial_price=Decimal("100"),
        steps=20,
        seed=42,
    )
    second = run_scenario(
        scenario_name="bull_market",
        initial_price=Decimal("100"),
        steps=20,
        seed=42,
    )

    assert first == second


def test_different_seed_changes_path() -> None:
    first = run_scenario(
        scenario_name="high_volatility",
        initial_price=Decimal("100"),
        steps=20,
        seed=1,
    )
    second = run_scenario(
        scenario_name="high_volatility",
        initial_price=Decimal("100"),
        steps=20,
        seed=2,
    )

    assert first != second


def test_scenario_preserves_positive_prices() -> None:
    points = run_scenario(
        scenario_name="inflation_shock",
        initial_price=Decimal("1"),
        steps=500,
        seed=99,
    )

    assert len(points) == 500
    assert all(point.price > 0 for point in points)


def test_catalog_contains_initial_educational_scenarios() -> None:
    assert {
        "bull_market",
        "bear_market",
        "high_volatility",
        "inflation_shock",
        "rate_cut_rally",
    }.issubset(SCENARIOS)


@pytest.mark.parametrize("steps", [0, 5001])
def test_invalid_step_count_is_rejected(steps: int) -> None:
    with pytest.raises(ValueError, match="steps must be between"):
        run_scenario(
            scenario_name="bull_market",
            initial_price=Decimal("100"),
            steps=steps,
            seed=1,
        )


def test_unknown_scenario_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown scenario"):
        run_scenario(
            scenario_name="unknown",
            initial_price=Decimal("100"),
            steps=10,
            seed=1,
        )
