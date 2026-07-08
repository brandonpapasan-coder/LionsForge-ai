from tests.conftest import auth_headers


def test_investment_thesis_endpoint(client):
    headers = auth_headers(client)
    response = client.get("/api/v1/research/thesis/AAPL", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["evidence_count"] >= 2
    assert payload["bull_case"]
    assert payload["bear_case"]
