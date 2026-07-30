"""Internal alpha lifecycle transitions."""

from .models import TesterState


_ALLOWED = {
    TesterState.INVITED: {TesterState.APPROVED},
    TesterState.APPROVED: {TesterState.ACTIVE},
    TesterState.ACTIVE: {TesterState.COMPLETED, TesterState.ARCHIVED},
    TesterState.COMPLETED: {TesterState.ARCHIVED},
    TesterState.ARCHIVED: set(),
}


def can_transition(current: TesterState, target: TesterState) -> bool:
    return target in _ALLOWED[current]
