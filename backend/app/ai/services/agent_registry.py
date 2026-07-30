"""Agent registry for Onyxmane AI orchestration.

Provides a central location for registering and retrieving specialized agents.
"""

from typing import Dict, Any


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}

    def register(self, name: str, agent: Any) -> None:
        self._agents[name] = agent

    def get(self, name: str) -> Any:
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())
