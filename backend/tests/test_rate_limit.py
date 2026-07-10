from fastapi.testclient import TestClient

from app.core.rate_limit import rate_limiter
from app.main import app, settings


def test_rate_limit_blocks_excess_requests(monkeypatch):
    rate_limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_requests", 2)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)

    with TestClient(app) as client:
        first = client.get("/platform")
        second = client.get("/platform")
        blocked = client.get("/platform")

    assert first.status_code == 200
    assert first.headers["x-ratelimit-limit"] == "2"
    assert first.headers["x-ratelimit-remaining"] == "1"
    assert second.status_code == 200
    assert second.headers["x-ratelimit-remaining"] == "0"
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Rate limit exceeded."}
    assert blocked.headers["retry-after"] == "60"
    rate_limiter.reset()


def test_operational_endpoints_are_exempt_from_rate_limiting(monkeypatch):
    rate_limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_requests", 1)

    with TestClient(app) as client:
        for _ in range(3):
            assert client.get("/health").status_code == 200
            assert client.get("/ready").status_code == 200
            assert client.get("/metrics").status_code == 200

    rate_limiter.reset()


def test_rate_limiting_can_be_disabled(monkeypatch):
    rate_limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_requests", 1)

    with TestClient(app) as client:
        responses = [client.get("/platform") for _ in range(3)]

    assert all(response.status_code == 200 for response in responses)
    rate_limiter.reset()
