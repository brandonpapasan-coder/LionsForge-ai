from datetime import datetime, timedelta, timezone

from app.internal_alpha.experiments import AlphaExperiment, validate_experiment


NOW = datetime(2026, 7, 30, 20, tzinfo=timezone.utc)
CANDIDATE = "a" * 40


def build(**changes: object) -> AlphaExperiment:
    values: dict[str, object] = {
        "experiment_id": "experiment_0001",
        "candidate_sha": CANDIDATE,
        "objective_code": "research_quality",
        "status": "ACTIVE",
        "created_at": NOW - timedelta(hours=1),
        "completed_at": None,
    }
    values.update(changes)
    return AlphaExperiment(**values)  # type: ignore[arg-type]


def test_accepts_active_candidate_bound_experiment() -> None:
    assert validate_experiment(build(), now=NOW)


def test_rejects_malformed_identity_candidate_and_future_creation() -> None:
    assert not validate_experiment(build(experiment_id="bad"), now=NOW)
    assert not validate_experiment(build(candidate_sha="not-a-sha"), now=NOW)
    assert not validate_experiment(build(created_at=NOW + timedelta(seconds=1)), now=NOW)


def test_completed_state_requires_bounded_completion_time() -> None:
    assert validate_experiment(
        build(status="COMPLETED", completed_at=NOW - timedelta(minutes=10)), now=NOW
    )
    assert not validate_experiment(build(status="COMPLETED"), now=NOW)
    assert not validate_experiment(
        build(status="COMPLETED", completed_at=NOW + timedelta(seconds=1)), now=NOW
    )


def test_nonterminal_state_rejects_completion_time() -> None:
    assert not validate_experiment(
        build(completed_at=NOW - timedelta(minutes=1)), now=NOW
    )
