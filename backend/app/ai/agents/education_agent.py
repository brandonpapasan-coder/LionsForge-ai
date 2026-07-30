"""Education Agent foundation for research-to-learning conversion."""

from dataclasses import dataclass


@dataclass
class LearningModule:
    title: str
    level: str


class EducationAgent:
    name = "education_agent"

    def create_module(self, title: str, level: str = "foundation") -> LearningModule:
        return LearningModule(title=title, level=level)
