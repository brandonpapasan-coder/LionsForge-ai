import pytest
from fastapi.testclient import TestClient

from app.main import app


_BASE_PATH = (
    "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/"
    "export-bundle/import-summary/batch-pipeline"
)
_ROUTE_CASES = (
    (_BASE_PATH, {"summaries": [{}]}),
    (
        _BASE_PATH + "/validate",
        {"summaries": [{}], "pipeline": {}},
    ),
    (
        _BASE_PATH + "/validate-response",
        {"summaries": [{}], "pipeline": {}, "response": {}},
    ),
)


@pytest.mark.parametrize(("path", "payload"), _ROUTE_CASES)
def test_pipeline_routes_are_registered_in_application_openapi(
    path: str,
    payload: dict,
) -> None:
    del payload
    operation = app.openapi()["paths"][path]["post"]

    assert operation["tags"] == ["internal-alpha-intelligence"]


@pytest.mark.parametrize(("path", "payload"), _ROUTE_CASES)
def test_registered_pipeline_routes_require_authentication(
    path: str,
    payload: dict,
) -> None:
    response = TestClient(app).post(path, json=payload)

    assert response.status_code in {401, 403}
