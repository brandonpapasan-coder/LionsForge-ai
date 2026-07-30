"""Internal alpha control plane models.

Privacy-safe structures for controlled validation workflows.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TesterState(str, Enum):
    INVITED = "invited"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class AlphaTesterRecord:
    tester_id: str
    candidate_sha: str
    state: TesterState
    created_at: datetime


@dataclass(frozen=True)
class AlphaExperimentRecord:
    experiment_id: str
    candidate_sha: str
    objective: str
    created_at: datetime
