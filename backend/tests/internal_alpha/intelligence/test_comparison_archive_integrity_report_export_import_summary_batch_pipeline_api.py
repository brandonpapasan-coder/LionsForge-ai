from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_import_summary_batch_pipeline import (
    router,
)


_PATH = (
    "/comparison/archive/integrity-report/export-bundle/import-summary/"
    "batch-pipeline"
)


def _payload() -> dict:
    return {"summaries": [{"summary": 1}]}


def test_batch_pipeline_api_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(_PATH, json=_payload())
    assert response.status_code in {401, 403}


def test_batch_pipeline_api_forwards_exact_summaries(monkeypatch):
    captured = {}
    expected = {
        "batch_result": {"batch": True},
        "diagnostics": {"diagnostics": True},
        "occurrence_projection": {"occurrences": True},
        "interpretation_notice": "bounded",
    }

    def fake_build(summaries):
        captured["summaries"] = summaries
        return expected

    monkeypatch.setattr(
        "app.api.routes."
        "internal_alpha_comparison_archive_integrity_report_export_import_summary_batch_pipeline."
        "build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        fake_build,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = _payload()
    response = TestClient(app).post(_PATH, json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    assert captured == payload


def test_batch_pipeline_request_rejects_extra_fields():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = _payload()
    payload["unexpected"] = True
    response = TestClient(app).post(_PATH, json=payload)
    assert response.status_code == 422


def test_batch_pipeline_request_rejects_empty_summaries():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    response = TestClient(app).post(_PATH, json={"summaries": []})
    assert response.status_code == 422


def test_batch_pipeline_request_accepts_100_summaries(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes."
        "internal_alpha_comparison_archive_integrity_report_export_import_summary_batch_pipeline."
        "build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        lambda summaries: {
            "batch_result": {"summary_count": len(summaries)},
            "diagnostics": {},
            "occurrence_projection": {},
            "interpretation_notice": "bounded",
        },
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    response = TestClient(app).post(_PATH, json={"summaries": [{}] * 100})
    assert response.status_code == 200
    assert response.json()["batch_result"]["summary_count"] == 100


def test_batch_pipeline_request_rejects_more_than_100_summaries():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    response = TestClient(app).post(_PATH, json={"summaries": [{}] * 101})
    assert response.status_code == 422


def test_batch_pipeline_api_is_registered_in_router_openapi():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/internal-alpha/intelligence")
    path = "/api/v1/internal-alpha/intelligence" + _PATH
    assert path in app.openapi()["paths"]
