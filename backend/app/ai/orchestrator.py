"""Onyxmane AI orchestration foundation.

Coordinates specialized research agents while preserving workflow state
and human review checkpoints.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ResearchMission:
    objective: str
    status: str = "created"
    agent_outputs: Dict[str, str] = field(default_factory=dict)


class AgentOrchestrator:
    """Coordinates research agents in a controlled workflow."""

    def __init__(self, agents: List[object] | None = None):
        self.agents = agents or []

    def execute(self, mission: ResearchMission) -> ResearchMission:
        mission.status = "in_progress"

        for agent in self.agents:
            name = agent.__class__.__name__
            mission.agent_outputs[name] = agent.run(mission.objective)

        mission.status = "awaiting_review"
        return mission
