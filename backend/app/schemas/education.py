from datetime import datetime

from pydantic import BaseModel, Field, model_validator


MASTERY_SCORE_THRESHOLD = 70


class LessonProgressUpdate(BaseModel):
    status: str = Field(pattern="^(not_started|in_progress|completed)$")
    score: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def require_passing_score_for_completion(self) -> "LessonProgressUpdate":
        if self.status == "completed" and (self.score is None or self.score < MASTERY_SCORE_THRESHOLD):
            raise ValueError(
                f"Completed lessons require a score of at least {MASTERY_SCORE_THRESHOLD}%."
            )
        return self


class LessonRead(BaseModel):
    slug: str
    title: str
    description: str
    level: str
    competency: str
    estimated_minutes: int
    prerequisites: list[str]
    status: str
    score: int | None
    completed_at: datetime | None
    path_state: str
    path_reason: str


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


class AssessmentQuestionRead(BaseModel):
    id: str
    prompt: str
    options: list[str]
    objective: str


class AdaptiveAssessmentRead(BaseModel):
    lesson_slug: str
    competency: str
    difficulty: str
    difficulty_reason: str
    question: AssessmentQuestionRead


class AssessmentSubmission(BaseModel):
    question_id: str
    selected_option: int = Field(ge=0)


class AssessmentResultRead(BaseModel):
    lesson_slug: str
    competency: str
    difficulty: str
    score: int
    passed: bool
    feedback: str
    learning_objective: str
    education_hub: EducationHubRead
