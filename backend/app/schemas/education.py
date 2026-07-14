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
    assessed_lessons: int
    average_score: int | None
    mastery_percent: int
    proficiency_band: str


class EducationHubRead(BaseModel):
    completed_lessons: int
    total_lessons: int
    assessed_lessons: int
    completion_percent: int
    average_score: int | None
    mastery_percent: int
    proficiency_band: str
    recommended_lesson_slug: str | None
    recommendation_reason: str
    lessons: list[LessonRead]
    competencies: list[CompetencySummary]
