from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.education import AssessmentAttempt
from app.models.user import User
from tests.conftest import auth_headers


TRENDS_URL = "/api/v1/education/assessment/trends"


def seed_attempts(email: str, competency: str, scores: list[int]) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        started = datetime(2026, 7, 19, 12, 0, 0)
        for index, score in enumerate(scores):
            db.add(
                AssessmentAttempt(
                    user_id=user.id,
                    lesson_slug="financial-statements-foundations",
                    competency=competency,
                    difficulty="foundation",
                    question_id=f"trend-question-{index}",
                    selected_option=0,
                    score=score,
                    passed=score >= 70,
                    created_at=started + timedelta(minutes=index),
                )
            )
        db.commit()


def trend_for(response, competency: str) -> dict:
    assert response.status_code == 200
    return next(item for item in response.json() if item["competency"] == competency)


def test_competency_trends_require_authentication(client):
    response = client.get(TRENDS_URL)
    assert response.status_code == 401


def test_improving_trend_compares_recent_and_prior_windows(client):
    email = "trend-improving@example.com"
    headers = auth_headers(client, email=email)
    seed_attempts(email, "financial-statements", [0, 0, 100, 100])

    trend = trend_for(client.get(TRENDS_URL, headers=headers), "financial-statements")
    assert trend == {
        "competency": "financial-statements",
        "attempt_count": 4,
        "recent_average": 100,
        "prior_average": 0,
        "direction": "improving",
        "explanation": "Recent performance improved by 100 points, from 0% to 100%.",
    }


def test_stable_and_declining_trends_are_explainable(client):
    stable_email = "trend-stable@example.com"
    stable_headers = auth_headers(client, email=stable_email)
    seed_attempts(stable_email, "financial-statements", [100, 0, 100, 0])
    stable = trend_for(client.get(TRENDS_URL, headers=stable_headers), "financial-statements")
    assert stable["direction"] == "stable"
    assert stable["recent_average"] == 50
    assert stable["prior_average"] == 50

    declining_email = "trend-declining@example.com"
    declining_headers = auth_headers(client, email=declining_email)
    seed_attempts(declining_email, "financial-statements", [100, 100, 0, 0])
    declining = trend_for(client.get(TRENDS_URL, headers=declining_headers), "financial-statements")
    assert declining["direction"] == "declining"
    assert declining["recent_average"] == 0
    assert declining["prior_average"] == 100
    assert "recommended review path" in declining["explanation"]


def test_insufficient_evidence_is_explicit_and_private(client):
    email = "trend-insufficient@example.com"
    headers = auth_headers(client, email=email)
    seed_attempts(email, "financial-statements", [100, 0, 100])

    response = client.get(TRENDS_URL, headers=headers)
    trend = trend_for(response, "financial-statements")
    assert trend["attempt_count"] == 3
    assert trend["recent_average"] is None
    assert trend["prior_average"] is None
    assert trend["direction"] == "insufficient_evidence"
    assert "1 more assessment attempt" in trend["explanation"]
    assert "correct_option" not in response.text
    assert "selected_option" not in response.text
    assert "question_id" not in response.text


def test_competency_trends_are_isolated_by_user(client):
    owner_email = "trend-owner@example.com"
    owner_headers = auth_headers(client, email=owner_email)
    seed_attempts(owner_email, "financial-statements", [0, 0, 100, 100])

    other_headers = auth_headers(client, email="trend-other@example.com")
    other = trend_for(client.get(TRENDS_URL, headers=other_headers), "financial-statements")
    assert other["attempt_count"] == 0
    assert other["direction"] == "insufficient_evidence"

    owner = trend_for(client.get(TRENDS_URL, headers=owner_headers), "financial-statements")
    assert owner["attempt_count"] == 4
    assert owner["direction"] == "improving"
