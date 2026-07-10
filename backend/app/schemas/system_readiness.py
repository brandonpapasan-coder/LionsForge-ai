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
