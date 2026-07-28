from datetime import UTC, datetime, timedelta

from app.services.promotion_rollout_status import _countdown


def test_unscheduled_countdown_reports_no_progress_or_remaining_time() -> None:
    evaluated_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)

    result = _countdown(start_at=None, launch_at=None, evaluated_at=evaluated_at)

    assert result == ("not_scheduled", None, None, None, None, None, None)


def test_future_countdown_reports_server_derived_progress() -> None:
    start_at = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    evaluated_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)
    launch_at = datetime(2026, 7, 28, 16, 0, tzinfo=UTC)

    state, normalized_start, normalized_launch, total, elapsed, remaining, progress = _countdown(
        start_at=start_at,
        launch_at=launch_at,
        evaluated_at=evaluated_at,
    )

    assert state == "scheduled"
    assert normalized_start == start_at
    assert normalized_launch == launch_at
    assert total == 14_400
    assert elapsed == 7_200
    assert remaining == 7_200
    assert progress == 50.0


def test_progress_is_clamped_to_zero_before_start() -> None:
    evaluated_at = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)
    start_at = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    launch_at = datetime(2026, 7, 28, 16, 0, tzinfo=UTC)

    result = _countdown(start_at=start_at, launch_at=launch_at, evaluated_at=evaluated_at)

    assert result[0] == "scheduled"
    assert result[4] == 0
    assert result[6] == 0.0


def test_elapsed_countdown_stops_at_zero_and_progress_reaches_100_without_authorizing_rollout() -> None:
    start_at = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    launch_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)
    evaluated_at = launch_at + timedelta(seconds=1)

    state, _, _, total, elapsed, remaining, progress = _countdown(
        start_at=start_at,
        launch_at=launch_at,
        evaluated_at=evaluated_at,
    )

    assert state == "reached"
    assert total == 7_200
    assert elapsed == 7_200
    assert remaining == 0
    assert progress == 100.0


def test_missing_start_time_preserves_countdown_without_guessing_progress() -> None:
    evaluated_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)
    launch_at = evaluated_at + timedelta(hours=1)

    result = _countdown(start_at=None, launch_at=launch_at, evaluated_at=evaluated_at)

    assert result == ("scheduled", None, launch_at, None, None, 3_600, None)


def test_invalid_progress_window_fails_closed_without_guessing_percentage() -> None:
    evaluated_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)
    launch_at = datetime(2026, 7, 28, 16, 0, tzinfo=UTC)
    start_at = launch_at

    result = _countdown(start_at=start_at, launch_at=launch_at, evaluated_at=evaluated_at)

    assert result[0] == "scheduled"
    assert result[3] is None
    assert result[4] is None
    assert result[5] == 7_200
    assert result[6] is None


def test_naive_countdown_timestamps_are_normalized_to_utc() -> None:
    evaluated_at = datetime(2026, 7, 28, 14, 0, tzinfo=UTC)
    start_at = datetime(2026, 7, 28, 13, 0)
    launch_at = datetime(2026, 7, 28, 15, 0)

    result = _countdown(start_at=start_at, launch_at=launch_at, evaluated_at=evaluated_at)

    assert result[1] == datetime(2026, 7, 28, 13, 0, tzinfo=UTC)
    assert result[2] == datetime(2026, 7, 28, 15, 0, tzinfo=UTC)
    assert result[3:] == (7_200, 3_600, 3_600, 50.0)
