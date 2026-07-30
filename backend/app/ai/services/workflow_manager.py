"""Workflow coordination for multi-agent research missions."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class WorkflowState:
    mission_id: str
    status: str = "created"
    completed_agents: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowManager:
    def create(self, mission_id: str) -> WorkflowState:
        return WorkflowState(mission_id=mission_id)

    def complete_agent(self, state: WorkflowState, agent_name: str) -> WorkflowState:
        state.completed_agents.append(agent_name)
        state.status = "in_progress"
        return state
