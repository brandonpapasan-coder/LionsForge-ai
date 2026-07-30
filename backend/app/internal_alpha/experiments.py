"""Internal alpha experiment registry foundation.

Tracks controlled validation experiments without enabling public release.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class AlphaExperiment:
    experiment_id: str
    candidate_sha: str
    objective: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


VALID_STATUSES = {
    "PLANNED",
    "ACTIVE",
    "REVIEW",
    "COMPLETED",
    "ARCHIVED",
}


def validate_experiment(experiment: AlphaExperiment) -> bool:
    return (
        bool(experiment.experiment_id)
        and bool(experiment.candidate_sha)
        and experiment.status in VALID_STATUSES
    )
