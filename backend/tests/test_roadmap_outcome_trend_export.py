from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.services.roadmap_outcome_trend_export import (
    export_roadmap_outcome_trends,
    validate_roadmap_outcome_trend_bundle,
)

NOW = datetime(2026, 7, 27, 18, 0, tzinfo=timezone.utc)
START = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
END = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)


def _source_bundle(user_id: int):
    return {
        "report": {
            "schema": "lionsforge.roadmap-action-outcome-report",
            "schema_version": 1,
            "generator_version": "1.0.0",
            "learner_user_id": user_id,
            "generated_at": "2026-07-27T18:00:00Z",
            "entries": [],
            "excluded_record_count": 0,
            "excluded_findings": [],
            "advisory_notice": "source notice",
        },
        "receipt": {"schema": "source"},
    }


def test_export_uses_owner_scoped_source_and_forwards_filters(monkeypatch):
    user = SimpleNamespace(id=9)
    captured = {}

    def fake_export(db, **kwargs):
        captured.update(kwargs)
        return _source_bundle(user.id)

    monkeypatch.setattr("app.services.roadmap_outcome_trend_export.export_roadmap_action_outcomes", fake_export)
    monkeypatch.setattr("app.services.roadmap_outcome_trend_export.validate_outcome_receipt", lambda receipt, report: [])

    bundle = export_roadmap_outcome_trends(
        Mock(),
        user=user,
        granularity="month",
        range_start=START,
        range_end=END,
        generated_at=NOW,
        template_slug="source-validation",
        reason_code="adds_not_yet_demonstrated_competency",
        outcome_status="completed",
    )

    assert captured["user"] is user
    assert captured["acted_after"] == START
    assert captured["acted_before"] == END
    assert captured["template_slug"] == "source-validation"
    assert captured["reason_code"] == "adds_not_yet_demonstrated_competency"
    assert captured["outcome_status"] == "completed"
    assert bundle["trends"]["learner_user_id"] == user.id
    assert bundle["trends"]["granularity"] == "month"


def test_export_fails_closed_on_invalid_source_or_learner_drift(monkeypatch):
    user = SimpleNamespace(id=9)
    monkeypatch.setattr(
        "app.services.roadmap_outcome_trend_export.export_roadmap_action_outcomes",
        lambda db, **kwargs: _source_bundle(user.id),
    )
    monkeypatch.setattr(
        "app.services.roadmap_outcome_trend_export.validate_outcome_receipt",
        lambda receipt, report: ["bad source"],
    )
    try:
        export_roadmap_outcome_trends(
            Mock(), user=user, granularity="day", range_start=START, range_end=END, generated_at=NOW
        )
        assert False, "expected source validation failure"
    except ValueError as exc:
        assert "source failed integrity" in str(exc)

    monkeypatch.setattr(
        "app.services.roadmap_outcome_trend_export.export_roadmap_action_outcomes",
        lambda db, **kwargs: _source_bundle(99),
    )
    monkeypatch.setattr("app.services.roadmap_outcome_trend_export.validate_outcome_receipt", lambda receipt, report: [])
    try:
        export_roadmap_outcome_trends(
            Mock(), user=user, granularity="day", range_start=START, range_end=END, generated_at=NOW
        )
        assert False, "expected learner binding failure"
    except ValueError as exc:
        assert "learner binding mismatch" in str(exc)


def test_bundle_validator_rejects_wrong_fields():
    assert validate_roadmap_outcome_trend_bundle({"trends": {}}) == {
        "valid": False,
        "findings": ["bundle fields are invalid"],
    }


def test_authenticated_routes_forward_query_filters_and_register_openapi(monkeypatch):
    user = SimpleNamespace(id=11)
    db = Mock()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db
    captured = {}

    def fake_export(db_arg, **kwargs):
        captured.update(kwargs)
        return {"trends": {"learner_user_id": user.id}, "receipt": {}}

    monkeypatch.setattr("app.api.routes.roadmap_outcome_trends.export_roadmap_outcome_trends", fake_export)
    client = TestClient(app)
    response = client.get(
        "/api/v1/education/roadmap-outcome-trends",
        params={
            "granularity": "week",
            "range_start": "2026-07-01T00:00:00Z",
            "range_end": "2026-08-01T00:00:00Z",
            "template_slug": "source-validation",
            "reason_code": "adds_not_yet_demonstrated_competency",
            "outcome_status": "completed",
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["user"] is user
    assert captured["granularity"] == "week"
    assert captured["range_start"] == START
    assert captured["range_end"] == END
    assert captured["template_slug"] == "source-validation"
    paths = app.openapi()["paths"]
    assert "/api/v1/education/roadmap-outcome-trends" in paths
    assert "/api/v1/education/roadmap-outcome-trends/validate" in paths
