from types import SimpleNamespace

from app.api.routes.release_countdown import get_release_countdown


def test_release_countdown_reports_verified_checkpoint_progress():
    result = get_release_countdown(current_user=SimpleNamespace(id=1))

    assert result.overall_completion_percent == 90
    assert result.completed_points == 90
    assert result.remaining_points == 10
    assert result.total_points == 100
    assert result.remaining_milestones == 1
    assert result.blocked_checkpoints == 1
    assert result.external_checkpoints == 10
    assert result.next_action == "Provision the Kubernetes staging cluster and lionsforge-staging namespace."

    phases = {phase.key: phase for phase in result.phases}
    assert phases["product"].completion_percent == 100
    assert phases["repository"].completion_percent == 100
    assert phases["staging"].completion_percent == 0
    assert phases["acceptance"].completion_percent == 0
    assert phases["staging"].checkpoints[0].state == "blocked"
    assert phases["staging"].checkpoints[0].issue_number == 29
    assert "not a calendar estimate" in result.disclaimer
