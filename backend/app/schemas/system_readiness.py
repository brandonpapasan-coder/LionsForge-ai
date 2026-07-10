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


class ProviderHealthRead(BaseModel):
    name: str
    status: Literal["available", "unavailable"]
    success_count: int
    failure_count: int
    consecutive_failures: int
    error_rate: float
    last_latency_ms: float | None
    last_error: str | None
    last_success_at: datetime | None
    last_failure_at: datetime | None


class ProviderHealthReport(BaseModel):
    providers: list[ProviderHealthRead]
    checked_at: datetime
