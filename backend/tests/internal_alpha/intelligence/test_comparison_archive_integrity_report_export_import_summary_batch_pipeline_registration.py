from fastapi.testclient import TestClient

from app.main import app


_PATH = (
    "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/"
    "export-bundle/import-summary/batch-pipeline"
)


def test_pipeline_route_is_registered_in_application_openapi() -> None:
    operation = app.openapi()["paths"][_PATH]["post"]

    assert operation["tags"] == ["internal-alpha-intelligence"]


def test_registered_pipeline_route_requires_authentication() -> None:
    response = TestClient(app).post(_PATH, json={"summaries": [{}]})

    assert response.status_code in {401, 403}
