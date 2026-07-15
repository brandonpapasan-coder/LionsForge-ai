from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ReadinessCheck(BaseModel):
    name: str
    status: Literal["pass", "fail"]
    detail: str


class SystemReadinessReport(BaseModel):
    status: Literal["ready", "degraded"]
    release: str
    checks: list[ReadinessCheck]
    modules: list[str]
    checked_at: datetime


class ErrorEventRead(BaseModel):
    request_id: str
    method: str
    path: str
    exception_type: str
    occurred_at: datetime


class OperationalMetricsReport(BaseModel):
    request_count: int
    server_error_count: int
    average_duration_ms: float
    status_codes: dict[int, int]
    application_exception_count: int
    exceptions_by_type: dict[str, int]
    last_exception: ErrorEventRead | None
    checked_at: datetime
