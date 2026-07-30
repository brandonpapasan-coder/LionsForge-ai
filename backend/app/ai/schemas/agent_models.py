"""Schemas for AI agent workflows."""

from dataclasses import dataclass


@dataclass
class AgentResult:
    agent_name: str
    output: str
    confidence: float = 0.0
    requires_review: bool = True
