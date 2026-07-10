from datetime import datetime

from pydantic import BaseModel, Field


class LearningModule(BaseModel):
    module_id: str
    title: str
    summary: str
    estimated_minutes: int = Field(ge=1)
    completed: bool = False


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


class LearningDashboard(BaseModel):
    learner_email: str
    recommended_course_id: str
    completed_modules: int
    total_modules: int
    courses: list[CourseCatalogItem]
