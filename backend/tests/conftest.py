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
from fastapi.testclient import TestClient

from app.db.session import Base, engine
from app.main import app


@pytest.fixture
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(reset_database) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
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
