from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles import router


_PATH = (
    "/comparison/archive/integrity-report/export-bundle/import-summary/"
    "batch-diagnostics/occurrences/validate-response"
)


def _payload() -> dict:
    return {
        "summaries": [{"summary": 1}],
        "batch_result": {"batch": 2},
        "diagnostics": {"diagnostics": 3},
        "occurrence_projection": {"occurrences": 4},
        "validation_response": {
            "valid": True,
            "findings": [],
            "interpretation_notice": "notice",
        },
    }


def test_occurrence_validation_response_api_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(_PATH, json=_payload())
    assert response.status_code in {401, 403}


def test_occurrence_validation_response_api_forwards_exact_payload(monkeypatch):
    captured = {}

    def fake_validate(
        summaries,
        batch_result,
        diagnostics,
        occurrence_projection,
        validation_response,
    ):
        captured["summaries"] = summaries
        captured["batch_result"] = batch_result
        captured["diagnostics"] = diagnostics
        captured["occurrence_projection"] = occurrence_projection
        captured["validation_response"] = validation_response
        return []

    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation_response",
        fake_validate,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = _payload()
    response = TestClient(app).post(_PATH, json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["findings"] == []
    assert "does not authorize" in response.json()["interpretation_notice"]
    assert captured == payload


def test_occurrence_validation_response_api_returns_findings(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation_response",
        lambda summaries, batch_result, diagnostics, occurrence_projection, validation_response: [
            "tampered"
        ],
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    response = TestClient(app).post(_PATH, json=_payload())
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["findings"] == ["tampered"]


def test_occurrence_validation_response_request_rejects_extra_fields():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = _payload()
    payload["unexpected"] = True
    response = TestClient(app).post(_PATH, json=payload)
    assert response.status_code == 422


def test_occurrence_validation_response_request_rejects_more_than_100_summaries():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = _payload()
    payload["summaries"] = [{}] * 101
    response = TestClient(app).post(_PATH, json=payload)
    assert response.status_code == 422


def test_occurrence_validation_response_api_is_registered_in_openapi():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/internal-alpha/intelligence")
    path = "/api/v1/internal-alpha/intelligence" + _PATH
    assert path in app.openapi()["paths"]
