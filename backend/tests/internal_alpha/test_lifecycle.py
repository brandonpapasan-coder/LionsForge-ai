from app.internal_alpha.lifecycle import can_transition
from app.internal_alpha.models import TesterState


def test_allows_only_forward_internal_alpha_transitions() -> None:
    assert can_transition(TesterState.INVITED, TesterState.APPROVED)
    assert can_transition(TesterState.APPROVED, TesterState.ACTIVE)
    assert can_transition(TesterState.ACTIVE, TesterState.COMPLETED)
    assert can_transition(TesterState.COMPLETED, TesterState.ARCHIVED)


def test_rejects_skips_reactivation_and_archived_changes() -> None:
    assert not can_transition(TesterState.INVITED, TesterState.ACTIVE)
    assert not can_transition(TesterState.COMPLETED, TesterState.ACTIVE)
    assert not can_transition(TesterState.ARCHIVED, TesterState.ACTIVE)
