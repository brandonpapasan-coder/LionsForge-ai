from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MentorFeedback:
    risk_tier: str
    summary: str
    observations: list[str]
    reflection_questions: list[str]
    disclaimer: str


def build_mentor_feedback(
    *,
    projected_return: Decimal,
    cash_ratio: Decimal,
    concentration_ratio: Decimal,
    position_count: int,
    scenario_name: str,
) -> MentorFeedback:
    loss = -projected_return if projected_return < 0 else Decimal("0")
    if loss >= Decimal("0.20") or concentration_ratio >= Decimal("0.75"):
        risk_tier = "high"
    elif loss >= Decimal("0.08") or concentration_ratio >= Decimal("0.50"):
        risk_tier = "elevated"
    else:
        risk_tier = "moderate"

    observations: list[str] = []
    if position_count == 0:
        observations.append("The portfolio currently holds no simulated positions, so scenario sensitivity is limited to cash.")
    elif concentration_ratio >= Decimal("0.50"):
        observations.append("A large share of simulated equity is concentrated in one position, increasing single-position sensitivity.")
    else:
        observations.append("No single simulated position exceeds half of starting equity in this stress run.")

    if cash_ratio >= Decimal("0.30"):
        observations.append("The simulated cash buffer absorbs part of the scenario impact and reduces portfolio volatility.")
    elif cash_ratio <= Decimal("0.10"):
        observations.append("The simulated cash buffer is small, so most equity remains exposed to position-level scenario movement.")
    else:
        observations.append("The simulated cash buffer provides partial protection but does not dominate portfolio behavior.")

    if projected_return <= Decimal("-0.10"):
        observations.append("This scenario produces a material simulated drawdown that merits closer review of exposure size and diversification.")
    elif projected_return < 0:
        observations.append("This scenario produces a simulated loss, but the drawdown remains below ten percent.")
    else:
        observations.append("This scenario produces a non-negative simulated result; that does not imply future market performance.")

    summary = (
        f"The {scenario_name.replace('_', ' ')} stress test indicates {risk_tier} simulated portfolio risk "
        f"with a projected return of {projected_return:.2%}."
    )
    reflection_questions = [
        "Which position contributes most to the simulated outcome, and why?",
        "How would changing the cash buffer alter the result?",
        "Would the portfolio behave differently under a second scenario or seed?",
    ]
    return MentorFeedback(
        risk_tier=risk_tier,
        summary=summary,
        observations=observations,
        reflection_questions=reflection_questions,
        disclaimer="Educational simulation only. This feedback is not financial advice, a prediction, or a recommendation to trade.",
    )
