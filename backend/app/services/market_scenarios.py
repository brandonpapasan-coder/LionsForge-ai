from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from random import Random

PRICE = Decimal("0.000001")


@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    drift: Decimal
    volatility: Decimal
    shock_probability: Decimal = Decimal("0")
    shock_magnitude: Decimal = Decimal("0")


@dataclass(frozen=True)
class ScenarioPoint:
    step: int
    return_rate: Decimal
    price: Decimal
    shock_applied: bool


SCENARIOS: dict[str, ScenarioDefinition] = {
    "bull_market": ScenarioDefinition(
        name="bull_market",
        drift=Decimal("0.0015"),
        volatility=Decimal("0.0080"),
    ),
    "bear_market": ScenarioDefinition(
        name="bear_market",
        drift=Decimal("-0.0012"),
        volatility=Decimal("0.0100"),
    ),
    "high_volatility": ScenarioDefinition(
        name="high_volatility",
        drift=Decimal("0.0000"),
        volatility=Decimal("0.0300"),
    ),
    "inflation_shock": ScenarioDefinition(
        name="inflation_shock",
        drift=Decimal("-0.0005"),
        volatility=Decimal("0.0140"),
        shock_probability=Decimal("0.08"),
        shock_magnitude=Decimal("-0.0450"),
    ),
    "rate_cut_rally": ScenarioDefinition(
        name="rate_cut_rally",
        drift=Decimal("0.0008"),
        volatility=Decimal("0.0110"),
        shock_probability=Decimal("0.06"),
        shock_magnitude=Decimal("0.0300"),
    ),
}


def _stable_seed(*parts: object) -> int:
    digest = sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def run_scenario(
    *,
    scenario_name: str,
    initial_price: Decimal,
    steps: int,
    seed: int,
) -> list[ScenarioPoint]:
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    if initial_price <= 0:
        raise ValueError("initial_price must be greater than zero")
    if steps < 1 or steps > 5000:
        raise ValueError("steps must be between 1 and 5000")

    definition = SCENARIOS[scenario_name]
    # Deterministic simulation replay requires a seeded PRNG. This generator is
    # never used for secrets, authentication, cryptography, or live execution.
    rng = Random(_stable_seed(scenario_name, seed, initial_price, steps))  # nosec B311
    current_price = initial_price.quantize(PRICE, rounding=ROUND_HALF_UP)
    points: list[ScenarioPoint] = []

    for step in range(1, steps + 1):
        normalized_noise = Decimal(str(rng.uniform(-1.0, 1.0)))
        return_rate = definition.drift + definition.volatility * normalized_noise
        shock_applied = rng.random() < float(definition.shock_probability)
        if shock_applied:
            return_rate += definition.shock_magnitude

        return_rate = return_rate.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        current_price = max(
            PRICE,
            (current_price * (Decimal("1") + return_rate)).quantize(PRICE, rounding=ROUND_HALF_UP),
        )
        points.append(
            ScenarioPoint(
                step=step,
                return_rate=return_rate,
                price=current_price,
                shock_applied=shock_applied,
            )
        )

    return points
