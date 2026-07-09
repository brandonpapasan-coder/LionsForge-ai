from tests.conftest import auth_headers, register_user


def test_register_login_and_me(client):
    user = register_user(client)
    assert user["email"] == "tester@example.com"

    headers = auth_headers(client, email="second@example.com")
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "second@example.com"


def test_protected_routes_require_token(client):
    response = client.get("/api/v1/watchlists")
    assert response.status_code == 401
