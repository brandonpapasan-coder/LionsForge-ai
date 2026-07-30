"""Strict internal-alpha experiment validation.

Experiments are metadata-only controls bound to one exact candidate. They do not
start infrastructure, create accounts, or authorize external beta activity.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from re import fullmatch
from typing import Optional


_ID = r"^[a-z0-9][a-z0-9_-]{7,63}$"
_SHA40 = r"^[0-9a-f]{40}$"
VALID_STATUSES = {"PLANNED", "ACTIVE", "REVIEW", "COMPLETED", "ARCHIVED"}


@dataclass(frozen=True)
class AlphaExperiment:
    experiment_id: str
    candidate_sha: str
    objective_code: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_experiment(experiment: AlphaExperiment, *, now: datetime | None = None) -> bool:
    """Return whether an experiment is a valid internal-only control record."""
    current = _utc(now or datetime.now(timezone.utc))
    created = _utc(experiment.created_at)
    completed = _utc(experiment.completed_at) if experiment.completed_at else None

    if not fullmatch(_ID, experiment.experiment_id):
        return False
    if not fullmatch(_SHA40, experiment.candidate_sha):
        return False
    if not fullmatch(_ID, experiment.objective_code):
        return False
    if experiment.status not in VALID_STATUSES:
        return False
    if created > current:
        return False
    if experiment.status in {"COMPLETED", "ARCHIVED"}:
        return completed is not None and created <= completed <= current
    return completed is None
