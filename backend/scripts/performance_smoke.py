import statistics
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app

PUBLIC_ENDPOINTS = [
    "/health",
    "/ready",
    "/platform",
]

PROTECTED_ENDPOINTS = [
    "/api/v1/market/quotes/AAPL",
    "/api/v1/news/company/AAPL",
    "/api/v1/research/context/AAPL",
    "/api/v1/research/evidence/AAPL",
    "/api/v1/research/confidence/AAPL",
    "/api/v1/research/thesis/AAPL",
]

MAX_P95_SECONDS = 0.35
REQUESTS_PER_ENDPOINT = 20


def get_auth_headers(client: TestClient) -> dict[str, str]:
    email = "perf@example.com"
    secret = "strongsecret123"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "secret": secret, "full_name": "Performance User"},
    )
    assert register.status_code in {201, 409}, register.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "secret": secret, "full_name": "Performance User"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def measure(client: TestClient, endpoint: str, headers: dict[str, str] | None = None) -> dict[str, float]:
    durations: list[float] = []
    for _ in range(REQUESTS_PER_ENDPOINT):
        start = time.perf_counter()
        response = client.get(endpoint, headers=headers)
        elapsed = time.perf_counter() - start
        assert response.status_code == 200, f"{endpoint} returned {response.status_code}: {response.text}"
        durations.append(elapsed)

    p95 = statistics.quantiles(durations, n=20)[18]
    return {
        "min": min(durations),
        "mean": statistics.mean(durations),
        "p95": p95,
        "max": max(durations),
    }


def main() -> None:
    results: dict[str, dict[str, float]] = {}
    with TestClient(app) as client:
        auth_headers = get_auth_headers(client)
        for endpoint in PUBLIC_ENDPOINTS:
            results[endpoint] = measure(client, endpoint)
        for endpoint in PROTECTED_ENDPOINTS:
            results[endpoint] = measure(client, endpoint, headers=auth_headers)

    slow = []
    for endpoint, stats in results.items():
        print(
            f"{endpoint}: min={stats['min']:.4f}s mean={stats['mean']:.4f}s "
            f"p95={stats['p95']:.4f}s max={stats['max']:.4f}s"
        )
        if stats["p95"] > MAX_P95_SECONDS:
            slow.append((endpoint, stats["p95"]))

    assert not slow, f"Performance smoke failed; p95 over {MAX_P95_SECONDS}s: {slow}"
    print("Performance smoke test passed.")


if __name__ == "__main__":
    main()
