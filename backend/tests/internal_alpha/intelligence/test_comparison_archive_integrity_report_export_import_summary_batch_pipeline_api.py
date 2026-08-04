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


def _canonical_pipeline(summary_count: int = 1) -> dict:
    return {
        "batch_result": {
            "summary_count": summary_count,
            "valid_count": summary_count,
            "invalid_count": 0,
            "finding_count": 0,
            "results": [
                {"index": index, "valid": True, "findings": []}
                for index in range(summary_count)
            ],
            "interpretation_notice": "batch bounded",
        },
        "diagnostics": {
            "summary_count": summary_count,
            "invalid_summary_count": 0,
            "invalid_indexes": [],
            "distinct_finding_count": 0,
            "finding_count": 0,
            "finding_frequencies": [],
            "interpretation_notice": "diagnostics bounded",
        },
        "occurrence_projection": {
            "summary_count": summary_count,
            "finding_count": 0,
            "distinct_finding_count": 0,
            "occurrences": [],
            "interpretation_notice": "occurrences bounded",
        },
        "interpretation_notice": "bounded",
    }


def test_batch_pipeline_api_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(_PATH, json=_payload())
    assert response.status_code in {401, 403}


def test_batch_pipeline_api_forwards_exact_summaries(monkeypatch):
    captured = {}
    expected = _canonical_pipeline()

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
        lambda summaries: _canonical_pipeline(len(summaries)),
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
