from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")
        platform = client.get("/platform")

    assert health.status_code == 200, health.text
    assert ready.status_code == 200, ready.text
    assert platform.status_code == 200, platform.text
    print("Backend smoke test passed.")


if __name__ == "__main__":
    main()
