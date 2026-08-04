from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_import_summary_batch_pipeline import (
    router,
)


_PATH = (
    "/comparison/archive/integrity-report/export-bundle/import-summary/"
    "batch-pipeline/validate-response"
)
_NOTICE = (
    "Pipeline validation-response verification proves deterministic recomputation "
    "of bounded transport-integrity results only. It does not authorize any release transition."
)


def _pipeline() -> dict:
    return {
        "batch_result": {
            "summary_count": 1,
            "valid_count": 1,
            "invalid_count": 0,
            "finding_count": 0,
            "results": [{"index": 0, "valid": True, "findings": []}],
            "interpretation_notice": "bounded batch",
        },
        "diagnostics": {
            "summary_count": 1,
            "invalid_summary_count": 0,
            "invalid_indexes": [],
            "distinct_finding_count": 0,
            "finding_count": 0,
            "finding_frequencies": [],
            "interpretation_notice": "bounded diagnostics",
        },
        "occurrence_projection": {
            "summary_count": 1,
            "finding_count": 0,
            "distinct_finding_count": 0,
            "occurrences": [],
            "interpretation_notice": "bounded occurrences",
        },
        "interpretation_notice": "bounded pipeline",
    }


def _payload() -> dict:
    return {
        "summaries": [{"summary": 1}],
        "pipeline": _pipeline(),
        "response": {
            "valid": True,
            "findings": [],
            "interpretation_notice": "bounded",
        },
    }


def _authenticated_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    return app


def test_batch_pipeline_validation_response_api_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(_PATH, json=_payload())
    assert response.status_code in {401, 403}


def test_batch_pipeline_validation_response_api_forwards_exact_inputs(monkeypatch):
    captured = {}

    def fake_validate(summaries, pipeline, response):
        captured["summaries"] = summaries
        captured["pipeline"] = pipeline
        captured["response"] = response
        return []

    monkeypatch.setattr(
        "app.api.routes."
        "internal_alpha_comparison_archive_integrity_report_export_import_summary_batch_pipeline."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response",
        fake_validate,
    )
    payload = _payload()
    response = TestClient(_authenticated_app()).post(_PATH, json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "findings": [],
        "interpretation_notice": _NOTICE,
    }
    assert captured == payload


def test_batch_pipeline_validation_response_api_returns_invalid_findings(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes."
        "internal_alpha_comparison_archive_integrity_report_export_import_summary_batch_pipeline."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response",
        lambda summaries, pipeline, response: [
            "valid does not match deterministic recomputation"
        ],
    )
    response = TestClient(_authenticated_app()).post(_PATH, json=_payload())

    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "findings": ["valid does not match deterministic recomputation"],
        "interpretation_notice": _NOTICE,
    }


def test_batch_pipeline_validation_response_request_rejects_extra_fields():
    payload = _payload()
    payload["unexpected"] = True
    response = TestClient(_authenticated_app()).post(_PATH, json=payload)
    assert response.status_code == 422


def test_batch_pipeline_validation_response_request_rejects_nested_pipeline_extra_fields():
    payload = _payload()
    payload["pipeline"]["batch_result"]["unexpected"] = True
    response = TestClient(_authenticated_app()).post(_PATH, json=payload)
    assert response.status_code == 422


def test_batch_pipeline_validation_response_request_rejects_nested_response_wrong_types():
    payload = _payload()
    payload["response"]["valid"] = 1
    response = TestClient(_authenticated_app()).post(_PATH, json=payload)
    assert response.status_code == 422


def test_batch_pipeline_validation_response_request_rejects_empty_summaries():
    payload = _payload()
    payload["summaries"] = []
    response = TestClient(_authenticated_app()).post(_PATH, json=payload)
    assert response.status_code == 422


def test_batch_pipeline_validation_response_request_accepts_100_summaries(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes."
        "internal_alpha_comparison_archive_integrity_report_export_import_summary_batch_pipeline."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response",
        lambda summaries, pipeline, response: [],
    )
    payload = _payload()
    payload["summaries"] = [{}] * 100
    response = TestClient(_authenticated_app()).post(_PATH, json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_batch_pipeline_validation_response_request_rejects_more_than_100_summaries():
    payload = _payload()
    payload["summaries"] = [{}] * 101
    response = TestClient(_authenticated_app()).post(_PATH, json=payload)
    assert response.status_code == 422


def test_batch_pipeline_validation_response_api_is_registered_in_router_openapi():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/internal-alpha/intelligence")
    path = "/api/v1/internal-alpha/intelligence" + _PATH
    assert path in app.openapi()["paths"]
