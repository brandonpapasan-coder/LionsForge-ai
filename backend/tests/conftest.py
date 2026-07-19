import os
import sys
from collections.abc import Generator
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_URL"] = "sqlite:///./test_lionsforge.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["ENVIRONMENT"] = "test"
os.environ["ENABLE_LEGACY_FINANCE_MODULES"] = "false"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import build_api_router
from app.core.config import get_settings
from app.core.legacy_finance_config import LegacyFinanceSettings
from app.db.session import Base, engine
from app.main import app, lifespan
from app.services.assessments import ASSESSMENT_BANK

LEGACY_FINANCE_TEST_MODULES = {
    "test_advanced_alerts.py",
    "test_alert_intelligence.py",
    "test_alerts.py",
    "test_auth.py",
    "test_autonomous_portfolio_intelligence.py",
    "test_autonomous_portfolios.py",
    "test_companies.py",
    "test_decision_intelligence.py",
    "test_decisions.py",
    "test_event_intelligence.py",
    "test_events.py",
    "test_factors.py",
    "test_market.py",
    "test_market_learning_api.py",
    "test_market_learning_evidence_api.py",
    "test_market_learning_mastery.py",
    "test_market_learning_portfolio.py",
    "test_market_learning_progress_api.py",
    "test_market_learning_roadmap.py",
    "test_market_mentor_api.py",
    "test_market_scenario_api.py",
    "test_market_simulator.py",
    "test_portfolio_risk.py",
    "test_portfolios.py",
    "test_watchlists.py",
}


def build_legacy_finance_test_app() -> FastAPI:
    settings = get_settings()
    legacy_app = FastAPI(lifespan=lifespan)
    legacy_app.include_router(
        build_api_router(
            settings=settings,
            legacy_finance_settings=LegacyFinanceSettings(
                enable_legacy_finance_modules=True,
                _env_file=None,
            ),
        ),
        prefix=settings.api_prefix,
    )
    return legacy_app


legacy_finance_test_app = build_legacy_finance_test_app()


@pytest.fixture
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(request, reset_database) -> Generator[TestClient, None, None]:
    selected_app = (
        legacy_finance_test_app
        if request.node.path.name in LEGACY_FINANCE_TEST_MODULES
        else app
    )
    with TestClient(selected_app) as test_client:
        yield test_client


def register_user(client: TestClient, email: str = "tester@example.com", secret: str = "strongsecret123"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "secret": secret, "full_name": "Test User"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(client: TestClient, email: str = "tester@example.com", secret: str = "strongsecret123"):
    register_user(client, email=email, secret=secret)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "secret": secret, "full_name": "Test User"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def pass_current_assessment(client: TestClient, headers: dict[str, str]) -> dict:
    assessment_response = client.get("/api/v1/education/assessment", headers=headers)
    assert assessment_response.status_code == 200
    assessment = assessment_response.json()
    question = ASSESSMENT_BANK[assessment["lesson_slug"]][assessment["difficulty"]]
    result = client.post(
        "/api/v1/education/assessment",
        headers=headers,
        json={
            "question_id": assessment["question"]["id"],
            "selected_option": question["correct_option"],
        },
    )
    assert result.status_code == 200
    assert result.json()["passed"] is True
    return result.json()
