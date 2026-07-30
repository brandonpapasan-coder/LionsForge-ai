"""Knowledge Agent foundation for converting research into reusable knowledge."""

from dataclasses import dataclass


@dataclass
class KnowledgeObject:
    title: str
    summary: str


class KnowledgeAgent:
    name = "knowledge_agent"

    def create(self, title: str, summary: str) -> KnowledgeObject:
        return KnowledgeObject(title=title, summary=summary)
