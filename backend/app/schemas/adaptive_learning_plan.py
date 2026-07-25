from typing import Literal

from pydantic import BaseModel, Field


class LearningPlanSignalRead(BaseModel):
    kind: Literal[
        "lesson_progress",
        "assessment_score",
        "failure_streak",
        "competency_trend",
        "prerequisite_status",
    ]
    reference: str
    value: str
    explanation: str
    measured: bool = True


class LearningPlanItemRead(BaseModel):
    sequence: int = Field(ge=1)
    lesson_slug: str
    title: str
    target_competency: str
    recommended_difficulty: Literal["foundation", "intermediate", "advanced"]
    priority: int = Field(ge=0)
    state: Literal["remediation", "recommended", "available", "locked"]
    reason: str
    mastery_threshold: int = Field(ge=0, le=100)
    prerequisite_slugs: list[str]
    signals: list[LearningPlanSignalRead]


class AdaptiveLearningPlanRead(BaseModel):
    status: Literal["active", "completed"]
    generated_from: Literal["measured_rules"] = "measured_rules"
    advisory_notice: str
    items: list[LearningPlanItemRead]
