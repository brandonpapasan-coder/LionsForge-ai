from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GovernanceTraceItem(BaseModel):
    action_id: int
    evidence_id: int
    impact_level: Literal["high_attention", "review_required", "informational"]
    governing_rule: str
    status: Literal["open", "acknowledged", "deferred", "resolved"]
    reason: str
    action_text: str
    supporting_event_ids: list[str]
    age_days: int
    age_bucket: str
    overdue: bool
    reopen_count: int
    created_at: datetime
    updated_at: datetime


class GovernanceMetric(BaseModel):
    key: str
    label: str
    count: int
    action_ids: list[int]


class GovernanceThroughput(BaseModel):
    resolved_transitions: int
    reopened_transitions: int
    net_resolved: int
    window_days: int
    action_ids: list[int]


class ResearchGovernanceDashboard(BaseModel):
    project_id: int
    generated_at: datetime
    total_actions: int
    status_metrics: list[GovernanceMetric]
    impact_metrics: list[GovernanceMetric]
    rule_metrics: list[GovernanceMetric]
    aging_metrics: list[GovernanceMetric]
    overdue_count: int
    repeatedly_reopened_count: int
    throughput: GovernanceThroughput
    trace_items: list[GovernanceTraceItem]
    disclaimer: str
