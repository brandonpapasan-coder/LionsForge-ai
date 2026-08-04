import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles import router
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences,
)


def _batch_result() -> dict:
    return {
        "summary_count": 3,
        "valid_count": 1,
        "invalid_count": 2,
        "finding_count": 4,
        "results": [
            {"index": 0, "valid": False, "findings": ["z", "a", "a"]},
            {"index": 1, "valid": True, "findings": []},
            {"index": 2, "valid": False, "findings": ["a"]},
        ],
        "interpretation_notice": "batch",
    }


def _diagnostics() -> dict:
    return {
        "summary_count": 3,
        "invalid_summary_count": 2,
        "invalid_indexes": [0, 2],
        "distinct_finding_count": 2,
        "finding_count": 4,
        "finding_frequencies": [
            {"finding": "a", "count": 3},
            {"finding": "z", "count": 1},
        ],
        "interpretation_notice": "diagnostics",
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


def _api_diagnostics() -> dict:
    return {
        "summary_count": 1,
        "invalid_summary_count": 0,
        "invalid_indexes": [],
        "distinct_finding_count": 0,
        "finding_count": 0,
        "finding_frequencies": [],
        "interpretation_notice": "diagnostics",
    }


def _api_payload() -> dict:
    return {
        "summaries": [{"a": 1}],
        "batch_result": _api_batch_result(),
        "diagnostics": _api_diagnostics(),
    }


def test_batch_diagnostic_occurrences_are_stable_and_located(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        lambda summaries, batch_result, diagnostics: [],
    )
    result = build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
        [{}, {}, {}], _batch_result(), _diagnostics()
    )
    assert result["summary_count"] == 3
    assert result["finding_count"] == 4
    assert result["distinct_finding_count"] == 2
    assert result["occurrences"] == [
        {
            "finding": "a",
            "occurrence_count": 3,
            "affected_summary_count": 2,
            "summary_indexes": [0, 2],
        },
        {
            "finding": "z",
            "occurrence_count": 1,
            "affected_summary_count": 1,
            "summary_indexes": [0],
        },
    ]
    assert "do not authorize" in result["interpretation_notice"]


def test_batch_diagnostic_occurrences_reject_invalid_diagnostics(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        lambda summaries, batch_result, diagnostics: ["tampered"],
    )
    with pytest.raises(ValueError, match="tampered"):
        build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
            [{}], _batch_result(), _diagnostics()
        )


def test_batch_diagnostic_occurrences_api_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/occurrences",
        json=_api_payload(),
    )
    assert response.status_code in {401, 403}


def test_batch_diagnostic_occurrences_api_forwards_exact_payload(monkeypatch):
    captured = {}

    def fake_build(summaries, batch_result, diagnostics):
        captured["summaries"] = summaries
        captured["batch_result"] = batch_result
        captured["diagnostics"] = diagnostics
        return {"ok": True}

    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        fake_build,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = _api_payload()
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/occurrences",
        json=payload,
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert captured == payload


def test_batch_diagnostic_occurrences_api_maps_invalid_input_to_422(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        lambda summaries, batch_result, diagnostics: (_ for _ in ()).throw(
            ValueError("invalid diagnostics")
        ),
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/occurrences",
        json=_api_payload(),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid diagnostics"


def test_batch_diagnostic_occurrences_api_is_registered_in_openapi():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/internal-alpha/intelligence")
    path = "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/occurrences"
    assert path in app.openapi()["paths"]


def test_batch_diagnostic_occurrences_request_rejects_more_than_100_summaries():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = _api_payload()
    payload["summaries"] = [{}] * 101
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/occurrences",
        json=payload,
    )
    assert response.status_code == 422
