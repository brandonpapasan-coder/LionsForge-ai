from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AdvancedAlertCategory = Literal[
    "earnings",
    "sec_filing",
    "analyst_change",
    "macro_event",
    "portfolio_risk",
]
AlertSeverity = Literal["info", "warning", "critical"]


class AdvancedAlertCreate(BaseModel):
    category: AdvancedAlertCategory
    headline: str = Field(min_length=3, max_length=160)
    detail: str = Field(min_length=3, max_length=2000)
    symbol: str | None = Field(default=None, min_length=1, max_length=12)
    severity: AlertSeverity = "info"
    event_at: datetime | None = None
    source_label: str | None = Field(default=None, max_length=120)
    portfolio_id: int | None = Field(default=None, gt=0)
    risk_score: int | None = Field(default=None, ge=0, le=100)
    threshold: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_category_fields(self) -> "AdvancedAlertCreate":
        if self.category == "portfolio_risk":
            if self.portfolio_id is None or self.risk_score is None or self.threshold is None:
                raise ValueError("portfolio_risk alerts require portfolio_id, risk_score, and threshold")
            if self.risk_score < self.threshold:
                raise ValueError("risk_score must meet or exceed threshold")
        return self


class AdvancedAlertRead(BaseModel):
    event_id: str
    notification_id: int
    category: AdvancedAlertCategory
    symbol: str | None = None
    severity: AlertSeverity
    title: str
    message: str
    event_at: datetime | None = None
    source_label: str | None = None
    delivery_status: str
    created_at: datetime
