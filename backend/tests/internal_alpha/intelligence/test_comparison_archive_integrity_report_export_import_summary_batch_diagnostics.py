import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles import router
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostics import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics,
)


def _batch_result() -> dict:
    return {
        "summary_count": 3,
        "valid_count": 1,
        "invalid_count": 2,
        "finding_count": 3,
        "results": [
            {"index": 0, "valid": False, "findings": ["z", "a"]},
            {"index": 1, "valid": True, "findings": []},
            {"index": 2, "valid": False, "findings": ["a"]},
        ],
        "interpretation_notice": "batch",
    }


def _api_batch_result() -> dict:
    return {
        "summary_count": 1,
        "valid_count": 1,
        "invalid_count": 0,
        "finding_count": 0,
        "results": [{"index": 0, "valid": True, "findings": []}],
        "interpretation_notice": "batch",
    }


def test_batch_diagnostics_are_stable_and_sorted(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostics.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result",
        lambda summaries, batch_result: [],
    )
    diagnostics = build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
        [{}, {}, {}], _batch_result()
    )
    assert diagnostics["invalid_indexes"] == [0, 2]
    assert diagnostics["invalid_summary_count"] == 2
    assert diagnostics["distinct_finding_count"] == 2
    assert diagnostics["finding_count"] == 3
    assert diagnostics["finding_frequencies"] == [
        {"finding": "a", "count": 2},
        {"finding": "z", "count": 1},
    ]
    assert "do not authorize" in diagnostics["interpretation_notice"]


def test_batch_diagnostics_reject_invalid_batch_result(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostics.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result",
        lambda summaries, batch_result: ["tampered"],
    )
    with pytest.raises(ValueError, match="tampered"):
        build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
            [{}], _batch_result()
        )


def test_batch_diagnostics_api_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics",
        json={"summaries": [{}], "batch_result": _api_batch_result()},
    )
    assert response.status_code in {401, 403}


def test_batch_diagnostics_api_forwards_exact_payload(monkeypatch):
    captured = {}

    def fake_build(summaries, batch_result):
        captured["summaries"] = summaries
        captured["batch_result"] = batch_result
        return {"ok": True}

    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        fake_build,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = {"summaries": [{"a": 1}], "batch_result": _api_batch_result()}
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics",
        json=payload,
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert captured == payload


def test_batch_diagnostics_api_maps_invalid_result_to_422(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        lambda summaries, batch_result: (_ for _ in ()).throw(ValueError("invalid batch")),
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics",
        json={"summaries": [{}], "batch_result": _api_batch_result()},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid batch"


def test_batch_diagnostics_api_is_registered_in_openapi():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/internal-alpha/intelligence")
    path = "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics"
    assert path in app.openapi()["paths"]


def test_batch_diagnostics_request_rejects_more_than_100_summaries():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics",
        json={"summaries": [{}] * 101, "batch_result": _api_batch_result()},
    )
    assert response.status_code == 422
