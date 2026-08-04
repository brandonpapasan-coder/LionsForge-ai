from copy import deepcopy

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles import (
    router,
)


_BASE = (
    "/comparison/archive/integrity-report/export-bundle/import-summary"
)


def _batch_result() -> dict[str, object]:
    return {
        "summary_count": 1,
        "valid_count": 1,
        "invalid_count": 0,
        "finding_count": 0,
        "results": [{"index": 0, "valid": True, "findings": []}],
        "interpretation_notice": "batch notice",
    }


def _diagnostics() -> dict[str, object]:
    return {
        "summary_count": 1,
        "invalid_summary_count": 0,
        "invalid_indexes": [],
        "distinct_finding_count": 0,
        "finding_count": 0,
        "finding_frequencies": [],
        "interpretation_notice": "diagnostics notice",
    }


def _occurrence_projection() -> dict[str, object]:
    return {
        "summary_count": 1,
        "finding_count": 0,
        "distinct_finding_count": 0,
        "occurrences": [],
        "interpretation_notice": "occurrence notice",
    }


def _validation_response() -> dict[str, object]:
    return {
        "valid": True,
        "findings": [],
        "interpretation_notice": "validation notice",
    }


def _payload() -> dict[str, object]:
    return {
        "summaries": [{"summary": 1}],
        "batch_result": _batch_result(),
        "diagnostics": _diagnostics(),
        "occurrence_projection": _occurrence_projection(),
        "validation_response": _validation_response(),
    }


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: object()
    return TestClient(app)


@pytest.mark.parametrize(
    ("path", "included_fields", "tampered_field"),
    [
        (
            f"{_BASE}/validate-batch-result",
            ("summaries", "batch_result"),
            "batch_result",
        ),
        (
            f"{_BASE}/batch-diagnostics",
            ("summaries", "batch_result"),
            "batch_result",
        ),
        (
            f"{_BASE}/batch-diagnostics/validate",
            ("summaries", "batch_result", "diagnostics"),
            "diagnostics",
        ),
        (
            f"{_BASE}/batch-diagnostics/occurrences",
            ("summaries", "batch_result", "diagnostics"),
            "diagnostics",
        ),
        (
            f"{_BASE}/batch-diagnostics/occurrences/validate",
            (
                "summaries",
                "batch_result",
                "diagnostics",
                "occurrence_projection",
            ),
            "occurrence_projection",
        ),
        (
            f"{_BASE}/batch-diagnostics/occurrences/validate-response",
            (
                "summaries",
                "batch_result",
                "diagnostics",
                "occurrence_projection",
                "validation_response",
            ),
            "validation_response",
        ),
    ],
)
def test_endpoints_reject_nested_extra_fields_before_handler_execution(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    included_fields: tuple[str, ...],
    tampered_field: str,
) -> None:
    called = False

    def fail_if_called(*args: object, **kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("handler dependency should not run")

    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_result",
        fail_if_called,
    )
    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles."
        "build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        fail_if_called,
    )
    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        fail_if_called,
    )
    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles."
        "build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        fail_if_called,
    )
    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        fail_if_called,
    )
    monkeypatch.setattr(
        "app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation_response",
        fail_if_called,
    )

    complete = _payload()
    payload = {field: deepcopy(complete[field]) for field in included_fields}
    nested = payload[tampered_field]
    assert isinstance(nested, dict)
    nested["unexpected"] = True

    response = _client().post(path, json=payload)

    assert response.status_code == 422
    assert called is False
    assert any(
        error["type"] == "extra_forbidden"
        and tampered_field in error["loc"]
        for error in response.json()["detail"]
    )


@pytest.mark.parametrize(
    ("path", "included_fields", "target_field"),
    [
        (
            f"{_BASE}/validate-batch-result",
            ("summaries", "batch_result"),
            "batch_result",
        ),
        (
            f"{_BASE}/batch-diagnostics/validate",
            ("summaries", "batch_result", "diagnostics"),
            "diagnostics",
        ),
        (
            f"{_BASE}/batch-diagnostics/occurrences/validate",
            (
                "summaries",
                "batch_result",
                "diagnostics",
                "occurrence_projection",
            ),
            "occurrence_projection",
        ),
    ],
)
def test_endpoints_reject_coercive_nested_counter_types(
    path: str,
    included_fields: tuple[str, ...],
    target_field: str,
) -> None:
    complete = _payload()
    payload = {field: deepcopy(complete[field]) for field in included_fields}
    nested = payload[target_field]
    assert isinstance(nested, dict)
    nested["summary_count"] = "1"

    response = _client().post(path, json=payload)

    assert response.status_code == 422
    assert any(
        error["type"] == "int_type" and target_field in error["loc"]
        for error in response.json()["detail"]
    )


def test_validation_response_endpoint_rejects_coercive_valid_flag() -> None:
    payload = _payload()
    validation_response = payload["validation_response"]
    assert isinstance(validation_response, dict)
    validation_response["valid"] = 1

    response = _client().post(
        f"{_BASE}/batch-diagnostics/occurrences/validate-response",
        json=payload,
    )

    assert response.status_code == 422
    assert any(
        error["type"] == "bool_type"
        and "validation_response" in error["loc"]
        for error in response.json()["detail"]
    )
