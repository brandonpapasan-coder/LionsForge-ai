from typing import TypedDict


class PracticumObjectiveDefinition(TypedDict):
    objective_key: str
    sequence: int
    title: str
    description: str
    competency: str
    required_evidence_categories: list[str]
    minimum_evidence_count: int
    reflection_required: bool
    human_review_required: bool


class PracticumTemplateDefinition(TypedDict):
    slug: str
    version: int
    title: str
    description: str
    estimated_minutes: int
    prerequisite_lesson_slugs: list[str]
    status: str
    objectives: list[PracticumObjectiveDefinition]


PRACTICUM_TEMPLATES: list[PracticumTemplateDefinition] = [
    {
        "slug": "evidence-backed-investigation",
        "version": 1,
        "title": "Evidence-Backed Investigation Practicum",
        "description": (
            "Demonstrate the ability to frame a research question, gather traceable evidence, "
            "separate evidence from inference, and prepare a conclusion for human review."
        ),
        "estimated_minutes": 240,
        "prerequisite_lesson_slugs": [
            "research-question-framing",
            "source-evaluation",
            "evidence-vs-inference",
        ],
        "status": "active",
        "objectives": [
            {
                "objective_key": "frame-investigation",
                "sequence": 1,
                "title": "Frame the investigation",
                "description": "Define a bounded research question, decision context, and success criteria.",
                "competency": "research-design",
                "required_evidence_categories": ["research_plan"],
                "minimum_evidence_count": 1,
                "reflection_required": True,
                "human_review_required": True,
            },
            {
                "objective_key": "evaluate-sources",
                "sequence": 2,
                "title": "Evaluate source quality",
                "description": "Use multiple traceable sources and explain their strengths, limitations, and relevance.",
                "competency": "source-evaluation",
                "required_evidence_categories": ["source", "provenance"],
                "minimum_evidence_count": 2,
                "reflection_required": True,
                "human_review_required": True,
            },
            {
                "objective_key": "defend-conclusion",
                "sequence": 3,
                "title": "Defend a conclusion",
                "description": "Present a conclusion that distinguishes evidence, inference, assumptions, and uncertainty.",
                "competency": "evidence-reasoning",
                "required_evidence_categories": ["claim", "counterevidence"],
                "minimum_evidence_count": 2,
                "reflection_required": True,
                "human_review_required": True,
            },
        ],
    }
]


def get_active_practicum_templates() -> list[PracticumTemplateDefinition]:
    return [template for template in PRACTICUM_TEMPLATES if template["status"] == "active"]


def get_practicum_template(slug: str, version: int | None = None) -> PracticumTemplateDefinition | None:
    matches = [template for template in PRACTICUM_TEMPLATES if template["slug"] == slug]
    if version is not None:
        return next((template for template in matches if template["version"] == version), None)
    return max(matches, key=lambda template: template["version"], default=None)
