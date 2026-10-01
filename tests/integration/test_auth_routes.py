"""HTTP authentication-route tests."""

from fastapi.testclient import TestClient

def test_secret_route_requires_a_logged_in_user(client: TestClient) -> None:
    credentials = {"email": " Member@Example.com ", "password": "correct-horse-battery"}
    signup_response = client.post("/auth/signup/", json=credentials)
    assert signup_response.status_code == 201
    assert signup_response.json()["email"] == "member@example.com"
    assert "password_hash" not in signup_response.json()

    login_payload = client.post("/auth/login/", json=credentials).json()
    assert login_payload["token_type"] == "bearer"
    assert login_payload["expires_in"] > 0
    assert login_payload["access_token"]

    anonymous_response = client.get("/auth/secret/")
    assert anonymous_response.status_code == 401
    assert anonymous_response.headers["WWW-Authenticate"] == "Bearer"

    authenticated_response = client.get("/auth/secret/", headers={"Authorization": f"Bearer {login_payload['access_token']}"})
    assert authenticated_response.status_code == 200
    assert authenticated_response.json() == {"message": "Authenticated access granted"}
