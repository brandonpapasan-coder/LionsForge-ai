from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.services.roadmap_outcome_insight_export import (
    export_roadmap_outcome_insights,
    validate_roadmap_outcome_insight_bundle,
)

NOW = datetime(2026, 7, 27, 16, 0, tzinfo=timezone.utc)


def _source_bundle(user_id: int):
    return {
        "report": {
            "schema": "lionsforge.roadmap-action-outcome-report",
            "schema_version": 1,
            "generator_version": "1.0.0",
            "learner_user_id": user_id,
            "generated_at": "2026-07-27T16:00:00Z",
            "entries": [],
            "excluded_record_count": 0,
            "excluded_findings": [],
            "advisory_notice": "source notice",
        },
        "receipt": {
            "schema": "source",
        },
    }


def test_export_uses_owner_scoped_canonical_source_and_forwards_filters(monkeypatch):
    user = SimpleNamespace(id=9)
    captured = {}

    def fake_export(db, **kwargs):
        captured.update(kwargs)
        return _source_bundle(user.id)

    monkeypatch.setattr("app.services.roadmap_outcome_insight_export.export_roadmap_action_outcomes", fake_export)
    monkeypatch.setattr("app.services.roadmap_outcome_insight_export.validate_outcome_receipt", lambda receipt, report: [])

    bundle = export_roadmap_outcome_insights(
        Mock(),
        user=user,
        generated_at=NOW,
        template_slug="source-validation",
        reason_code="adds_not_yet_demonstrated_competency",
        outcome_status="completed",
        acted_after=NOW,
        acted_before=NOW,
        completed_after=NOW,
        completed_before=NOW,
    )

    assert captured["user"] is user
    assert captured["template_slug"] == "source-validation"
    assert captured["reason_code"] == "adds_not_yet_demonstrated_competency"
    assert captured["outcome_status"] == "completed"
    assert bundle["insights"]["learner_user_id"] == user.id
    assert bundle["insights"]["total_action_count"] == 0


def test_export_fails_closed_on_invalid_source_or_learner_drift(monkeypatch):
    user = SimpleNamespace(id=9)
    monkeypatch.setattr(
        "app.services.roadmap_outcome_insight_export.export_roadmap_action_outcomes",
        lambda db, **kwargs: _source_bundle(user.id),
    )
    monkeypatch.setattr(
        "app.services.roadmap_outcome_insight_export.validate_outcome_receipt",
        lambda receipt, report: ["bad source"],
    )
    try:
        export_roadmap_outcome_insights(Mock(), user=user, generated_at=NOW)
        assert False, "expected source validation failure"
    except ValueError as exc:
        assert "source failed integrity" in str(exc)

    drifted = _source_bundle(99)
    monkeypatch.setattr(
        "app.services.roadmap_outcome_insight_export.export_roadmap_action_outcomes",
        lambda db, **kwargs: drifted,
    )
    monkeypatch.setattr("app.services.roadmap_outcome_insight_export.validate_outcome_receipt", lambda receipt, report: [])
    try:
        export_roadmap_outcome_insights(Mock(), user=user, generated_at=NOW)
        assert False, "expected learner binding failure"
    except ValueError as exc:
        assert "learner binding mismatch" in str(exc)


def test_bundle_validator_rejects_wrong_fields():
    result = validate_roadmap_outcome_insight_bundle({"insights": {}})
    assert result == {"valid": False, "findings": ["bundle fields are invalid"]}


def test_authenticated_routes_are_registered_and_forward_query_filters(monkeypatch):
    user = SimpleNamespace(id=11)
    db = Mock()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db
    captured = {}

    def fake_export(db_arg, **kwargs):
        captured.update(kwargs)
        return {"insights": {"learner_user_id": user.id}, "receipt": {}}

    monkeypatch.setattr("app.api.routes.roadmap_outcome_insights.export_roadmap_outcome_insights", fake_export)
    client = TestClient(app)
    response = client.get(
        "/api/education/roadmap-outcome-insights",
        params={
            "template_slug": "source-validation",
            "reason_code": "adds_not_yet_demonstrated_competency",
            "outcome_status": "completed",
            "acted_after": "2026-07-01T00:00:00Z",
            "acted_before": "2026-07-31T23:59:59Z",
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["user"] is user
    assert captured["template_slug"] == "source-validation"
    assert captured["outcome_status"] == "completed"
    paths = app.openapi()["paths"]
    assert "/api/education/roadmap-outcome-insights" in paths
    assert "/api/education/roadmap-outcome-insights/validate" in paths
