from app.core.security import get_secret_hash
from app.db.session import SessionLocal
from app.models.user import User
from app.services.research_report_service import build_research_report, list_research_reports
from tests.conftest import auth_headers


def create_test_user(db, email: str = "research@example.com") -> User:
    user = User(
        email=email,
        full_name="Research Test User",
        hashed_password=get_secret_hash("strongsecret123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_research_report_service_generates_and_persists(reset_database):
    db = SessionLocal()
    try:
        user = create_test_user(db)
        report = build_research_report("aapl", user=user, db=db, persist=True)
        saved = list_research_reports(db=db, user=user, symbol="AAPL")
    finally:
        db.close()

    assert report.metadata.symbol == "AAPL"
    assert report.metadata.version == 1
    assert report.metadata.confidence_level in {"low", "medium", "high"}
    assert report.evidence
    assert report.sections
    assert saved[0].report_id == report.metadata.report_id
    assert saved[0].symbol == "AAPL"


def test_research_report_versioning(reset_database):
    db = SessionLocal()
    try:
        user = create_test_user(db, email="versioning@example.com")
        first = build_research_report("MSFT", user=user, db=db, persist=True)
        second = build_research_report("MSFT", user=user, db=db, persist=True)
    finally:
        db.close()

    assert first.metadata.version == 1
    assert second.metadata.version == 2


def test_generate_research_report_endpoint(client):
    headers = auth_headers(client)

    response = client.post(
        "/api/v1/research/reports",
        json={"symbol": "AAPL", "persist": True},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["symbol"] == "AAPL"
    assert payload["metadata"]["version"] >= 1
    assert payload["metadata"]["confidence_level"] in {"low", "medium", "high"}
    assert payload["evidence"]
    assert payload["sections"]
    assert payload["executive_summary"]


def test_list_and_read_research_report_endpoints(client):
    headers = auth_headers(client)
    generated = client.post(
        "/api/v1/research/reports",
        json={"symbol": "NVDA", "persist": True},
        headers=headers,
    ).json()
    report_id = generated["metadata"]["report_id"]

    list_response = client.get("/api/v1/research/reports?symbol=NVDA", headers=headers)
    read_response = client.get(f"/api/v1/research/reports/{report_id}", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()["reports"][0]["report_id"] == report_id
    assert read_response.status_code == 200
    assert read_response.json()["report_id"] == report_id
    assert read_response.json()["symbol"] == "NVDA"


def test_read_missing_research_report_returns_404(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/research/reports/missing-report", headers=headers)
    assert response.status_code == 404
