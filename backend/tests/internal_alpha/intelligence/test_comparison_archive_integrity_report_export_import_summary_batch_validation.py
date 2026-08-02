from copy import deepcopy

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles import router
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch,
)
from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result,
)


def _summary(valid: bool = True) -> dict:
    return {
        "bundle": {},
        "canonical_byte_count": 1,
        "canonical_payload_sha256": "a" * 64,
        "export_bundle_sha256": "b" * 64,
        "interpretation_notice": "x" if valid else "y",
    }


def test_batch_result_validator_accepts_exact_recomputed_result(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary.validate_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda bundle: [],
    )
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary.serialize_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda bundle: b"{}",
    )
    summaries = [_summary()]
    expected = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(summaries)
    assert validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result(summaries, expected) == []


@pytest.mark.parametrize("field", ["summary_count", "valid_count", "invalid_count", "finding_count", "interpretation_notice"])
def test_batch_result_validator_detects_top_level_tampering(monkeypatch, field):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary.validate_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda bundle: [],
    )
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary.serialize_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda bundle: b"{}",
    )
    summaries = [_summary()]
    result = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(summaries)
    tampered = deepcopy(result)
    tampered[field] = -1 if field != "interpretation_notice" else "tampered"
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result(summaries, tampered)
    assert any(field in finding for finding in findings)


def test_batch_result_validator_detects_index_and_findings_tampering(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary.validate_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda bundle: [],
    )
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary.serialize_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda bundle: b"{}",
    )
    summaries = [_summary()]
    result = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(summaries)
    result["results"][0]["index"] = 9
    result["results"][0]["findings"] = ["tampered"]
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result(summaries, result)
    assert any("index mismatch" in finding for finding in findings)
    assert any("findings mismatch" in finding for finding in findings)


def test_batch_result_api_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/validate-batch-result",
        json={"summaries": [{}], "batch_result": {}},
    )
    assert response.status_code in {401, 403}


def test_batch_result_api_forwards_exact_payload(monkeypatch):
    captured = {}

    def fake_validate(summaries, batch_result):
        captured["summaries"] = summaries
        captured["batch_result"] = batch_result
        return []

    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result",
        fake_validate,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    payload = {"summaries": [{"a": 1}], "batch_result": {"b": 2}}
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/validate-batch-result",
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert captured == payload


def test_batch_result_api_is_registered_in_openapi():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/internal-alpha/intelligence")
    path = "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/export-bundle/import-summary/validate-batch-result"
    assert path in app.openapi()["paths"]


def test_batch_result_request_rejects_more_than_100_summaries():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    response = TestClient(app).post(
        "/comparison/archive/integrity-report/export-bundle/import-summary/validate-batch-result",
        json={"summaries": [{}] * 101, "batch_result": {}},
    )
    assert response.status_code == 422
