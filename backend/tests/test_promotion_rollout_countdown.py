from datetime import UTC, datetime, timedelta

from app.services.promotion_rollout_status import _countdown


def test_unscheduled_countdown_reports_no_remaining_time() -> None:
    evaluated_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)

    state, launch_at, remaining = _countdown(launch_at=None, evaluated_at=evaluated_at)

    assert state == "not_scheduled"
    assert launch_at is None
    assert remaining is None


def test_future_countdown_reports_non_negative_server_derived_seconds() -> None:
    evaluated_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)
    launch_at = evaluated_at + timedelta(days=2, hours=3, minutes=4, seconds=5)

    state, normalized_launch_at, remaining = _countdown(
        launch_at=launch_at,
        evaluated_at=evaluated_at,
    )

    assert state == "scheduled"
    assert normalized_launch_at == launch_at
    assert remaining == 183_845


def test_elapsed_countdown_stops_at_zero_without_authorizing_rollout() -> None:
    evaluated_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)
    launch_at = evaluated_at - timedelta(seconds=1)

    state, normalized_launch_at, remaining = _countdown(
        launch_at=launch_at,
        evaluated_at=evaluated_at,
    )

    assert state == "reached"
    assert normalized_launch_at == launch_at
    assert remaining == 0


def test_naive_launch_timestamp_is_normalized_to_utc() -> None:
    evaluated_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)
    launch_at = datetime(2026, 7, 28, 15, 0)

    state, normalized_launch_at, remaining = _countdown(
        launch_at=launch_at,
        evaluated_at=evaluated_at,
    )

    assert state == "scheduled"
    assert normalized_launch_at == datetime(2026, 7, 28, 15, 0, tzinfo=UTC)
    assert remaining == 3_600
