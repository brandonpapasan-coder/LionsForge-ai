"""Discovery Agent foundation for Onyxmane research workflows."""

from dataclasses import dataclass


@dataclass
class DiscoveryPlan:
    objective: str
    questions: list[str]
    evidence_needed: list[str]


class DiscoveryAgent:
    name = "discovery_agent"

    def create_plan(self, objective: str) -> DiscoveryPlan:
        return DiscoveryPlan(
            objective=objective,
            questions=[objective],
            evidence_needed=[],
        )
