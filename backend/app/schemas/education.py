from datetime import datetime

from pydantic import BaseModel, Field


class LessonProgressUpdate(BaseModel):
    status: str = Field(pattern="^(not_started|in_progress|completed)$")
    score: int | None = Field(default=None, ge=0, le=100)


class LessonRead(BaseModel):
    slug: str
    title: str
    description: str
    level: str
    competency: str
    estimated_minutes: int
    status: str
    score: int | None
    completed_at: datetime | None


class CompetencySummary(BaseModel):
    competency: str
    completed_lessons: int
    total_lessons: int
    mastery_percent: int


class EducationHubRead(BaseModel):
    completed_lessons: int
    total_lessons: int
    completion_percent: int
    lessons: list[LessonRead]
    competencies: list[CompetencySummary]
