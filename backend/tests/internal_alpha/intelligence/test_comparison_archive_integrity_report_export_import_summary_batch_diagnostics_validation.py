from copy import deepcopy

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles import router
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostics_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics,
)


def _batch_result() -> dict:
    return {
        "summary_count": 1,
        "valid_count": 1,
        "invalid_count": 0,
        "finding_count": 0,
        "results": [{"index": 0, "valid": True, "findings": []}],
        "interpretation_notice": "batch",
    }


def _diagnostics() -> dict:
    return {
        "summary_count": 2,
        "invalid_summary_count": 1,
        "invalid_indexes": [1],
        "distinct_finding_count": 1,
        "finding_count": 2,
        "finding_frequencies": [{"finding": "x", "count": 2}],
        "interpretation_notice": "notice",
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


def test_diagnostics_validator_accepts_exact_recomputed_value(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostics_validation.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        lambda summaries, batch_result: _diagnostics(),
    )
    assert (
        validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
            [{}, {}], {}, _diagnostics()
        )
        == []
    )


def test_diagnostics_validator_detects_top_level_and_frequency_tampering(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostics_validation.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        lambda summaries, batch_result: _diagnostics(),
    )
    tampered = deepcopy(_diagnostics())
    tampered["invalid_indexes"] = [0]
    tampered["finding_frequencies"][0]["count"] = 9
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
        [{}, {}], {}, tampered
    )
    assert any("invalid_indexes mismatch" in finding for finding in findings)
    assert any("count mismatch" in finding for finding in findings)


def test_diagnostics_validator_rejects_invalid_source(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostics_validation.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        lambda summaries, batch_result: (_ for _ in ()).throw(ValueError("bad source")),
    )
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics(
        [{}], {}, {}
    )
    assert findings == [
        "integrity report export import summary batch diagnostics source invalid: bad source"
    ]


def test_diagnostics_validation_api_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/validate",
        json={
            "summaries": [{}],
            "batch_result": _batch_result(),
            "diagnostics": _api_diagnostics(),
        },
    )
    assert response.status_code in {401, 403}


def test_diagnostics_validation_api_forwards_exact_payload(monkeypatch):
    captured = {}

    def fake_validate(summaries, batch_result, diagnostics):
        captured.update(
            summaries=summaries, batch_result=batch_result, diagnostics=diagnostics
        )
        return []

    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        fake_validate,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = {
        "summaries": [{"a": 1}],
        "batch_result": _batch_result(),
        "diagnostics": _api_diagnostics(),
    }
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/validate",
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert captured == payload


def test_diagnostics_validation_api_is_registered_in_openapi():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/internal-alpha/intelligence")
    path = "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/validate"
    assert path in app.openapi()["paths"]


def test_diagnostics_validation_request_rejects_more_than_100_summaries():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/batch-diagnostics/validate",
        json={
            "summaries": [{}] * 101,
            "batch_result": _batch_result(),
            "diagnostics": _api_diagnostics(),
        },
    )
    assert response.status_code == 422
