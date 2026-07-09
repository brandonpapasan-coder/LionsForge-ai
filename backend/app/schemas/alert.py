from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=12)
    condition: str = Field(..., pattern="^(above|below)$")
    target_price: Decimal = Field(..., gt=0)
    note: str | None = Field(default=None, max_length=240)


class AlertRead(BaseModel):
    id: int
    owner_id: int
    symbol: str
    condition: str
    target_price: Decimal
    note: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class AlertEvaluation(BaseModel):
    alert_id: int
    symbol: str
    condition: str
    target_price: Decimal
    current_price: Decimal
    triggered: bool
    notification_id: int | None = None


class AlertNotificationRead(BaseModel):
    id: int
    owner_id: int
    alert_id: int | None = None
    symbol: str | None = None
    notification_type: str
    severity: Literal["info", "warning", "critical"]
    title: str
    message: str
    delivery_channel: str
    delivery_status: str
    is_read: bool
    created_at: datetime
    read_at: datetime | None = None

    model_config = {"from_attributes": True}


class AlertAutomationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    rule_type: Literal["daily_market_summary", "portfolio_review", "watchlist_digest"]
    schedule: Literal["daily", "weekly"] = "daily"
    symbol: str | None = Field(default=None, max_length=12)


class AlertAutomationRuleRead(BaseModel):
    id: int
    owner_id: int
    name: str
    rule_type: str
    schedule: str
    symbol: str | None = None
    is_active: bool
    last_run_at: datetime | None = None

    model_config = {"from_attributes": True}


class AutomationRunResult(BaseModel):
    rule_id: int
    notification_id: int
    title: str
    delivery_status: str
