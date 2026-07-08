import statistics
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app

ENDPOINTS = [
    "/health",
    "/ready",
    "/platform",
    "/api/v1/market/quotes/AAPL",
    "/api/v1/news/company/AAPL",
    "/api/v1/research/context/AAPL",
    "/api/v1/research/evidence/AAPL",
    "/api/v1/research/confidence/AAPL",
    "/api/v1/research/thesis/AAPL",
]

MAX_P95_SECONDS = 0.25
REQUESTS_PER_ENDPOINT = 20


def measure(client: TestClient, endpoint: str) -> dict[str, float]:
    durations: list[float] = []
    for _ in range(REQUESTS_PER_ENDPOINT):
        start = time.perf_counter()
        response = client.get(endpoint)
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
    with TestClient(app) as client:
        results = {endpoint: measure(client, endpoint) for endpoint in ENDPOINTS}

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
