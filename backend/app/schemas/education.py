from datetime import datetime

from pydantic import BaseModel, Field


class LearningModule(BaseModel):
    module_id: str
    title: str
    summary: str
    estimated_minutes: int = Field(ge=1)
    completed: bool = False
    attempt_count: int = 0
    best_score: int | None = None


class CourseCatalogItem(BaseModel):
    course_id: str
    title: str
    level: str
    description: str
    modules: list[LearningModule]


class ModuleCompletionCreate(BaseModel):
    course_id: str
    module_id: str


class ModuleCompletionRead(BaseModel):
    course_id: str
    module_id: str
    completed_at: datetime


class LessonAssessment(BaseModel):
    question: str
    options: list[str]
    passing_score: int = Field(default=80, ge=0, le=100)


class LessonDetail(BaseModel):
    course_id: str
    module_id: str
    course_title: str
    title: str
    summary: str
    estimated_minutes: int
    objectives: list[str]
    key_points: list[str]
    assessment: LessonAssessment
    completed: bool = False
    attempt_count: int = 0
    best_score: int | None = None


class AssessmentSubmission(BaseModel):
    selected_option: int = Field(ge=0)


class AssessmentResult(BaseModel):
    score: int = Field(ge=0, le=100)
    passed: bool
    explanation: str
    completed_at: datetime | None = None
    attempt_count: int
    best_score: int


class LearningDashboard(BaseModel):
    learner_email: str
    recommended_course_id: str
    completed_modules: int
    total_modules: int
    mastery_average: int | None = None
    courses: list[CourseCatalogItem]
