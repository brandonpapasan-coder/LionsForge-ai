"""Execution layer for coordinated AI agents."""

from typing import Any


class AgentExecutionService:
    def __init__(self, registry: Any) -> None:
        self.registry = registry

    def execute(self, agent_name: str, payload: dict) -> dict:
        agent = self.registry.get(agent_name)
        if agent is None:
            return {
                "status": "failed",
                "reason": "agent_not_registered",
            }

        result = agent.run(payload)
        return {
            "status": "completed",
            "agent": agent_name,
            "result": result,
        }
