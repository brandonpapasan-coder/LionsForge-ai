def test_health_ready_and_root(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200

    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["name"] == "LionsForge AI"

    platform = client.get("/platform")
    assert platform.status_code == 200
    assert "modules" in platform.json()
