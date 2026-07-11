from datetime import datetime

from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: int
    detail: str


class DashboardAction(BaseModel):
    title: str
    reason: str
    href: str
    priority: str


class DashboardActivity(BaseModel):
    kind: str
    title: str
    summary: str | None
    href: str
    updated_at: datetime


class ExecutiveDashboard(BaseModel):
    greeting: str
    briefing: str
    metrics: list[DashboardMetric]
    next_actions: list[DashboardAction]
    recent_activity: list[DashboardActivity]
