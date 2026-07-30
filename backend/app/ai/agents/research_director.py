"""Research director agent interface for Onyxmane."""


class ResearchDirectorAgent:
    name = "research_director"

    def run(self, objective: str) -> str:
        return f"Research mission plan generated for: {objective}"
