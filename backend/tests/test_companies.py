def auth_headers(client):
    payload = {
        "email": "company-tests@example.com",
        "secret": "strongsecret123",
        "full_name": "Company Test User",
    }
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/login", json=payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_company_profile_crud(client):
    headers = auth_headers(client)
    create_response = client.post(
        "/api/v1/companies",
        json={
            "ticker": "aapl",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "country": "United States",
            "website": "https://www.apple.com",
            "description": "Consumer technology company.",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    company = create_response.json()
    assert company["ticker"] == "AAPL"
    assert company["name"] == "Apple Inc."

    get_response = client.get("/api/v1/companies/AAPL", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["ticker"] == "AAPL"

    list_response = client.get("/api/v1/companies?query=apple", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.patch(
        "/api/v1/companies/aapl",
        json={"sector": "Consumer Technology"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["sector"] == "Consumer Technology"

    duplicate_response = client.post(
        "/api/v1/companies",
        json={"ticker": "AAPL", "name": "Apple Duplicate"},
        headers=headers,
    )
    assert duplicate_response.status_code == 409

    delete_response = client.delete("/api/v1/companies/AAPL", headers=headers)
    assert delete_response.status_code == 204

    missing_response = client.get("/api/v1/companies/AAPL", headers=headers)
    assert missing_response.status_code == 404


def test_company_profiles_require_authentication(client):
    response = client.get("/api/v1/companies")
    assert response.status_code == 401
