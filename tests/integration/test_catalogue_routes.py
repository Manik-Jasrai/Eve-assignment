"""HTTP catalogue-route tests using the shared in-memory store."""

from fastapi.testclient import TestClient


def _headers(client: TestClient, email: str) -> dict[str, str]:
    credentials = {"email": email, "password": "correct-horse-battery"}
    assert client.post("/auth/signup/", json=credentials).status_code == 201
    token = client.post("/auth/login/", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_catalogue_routes_use_public_reads_and_authenticated_writes(client: TestClient) -> None:
    headers = _headers(client, "catalogue@example.com")
    assert client.get("/centres/").json() == {"items": [], "limit": 20, "offset": 0}
    assert client.post("/centres/", json={"name": "North Clinic", "location": "Delhi"}).status_code == 401

    centre = client.post("/centres/", headers=headers, json={"name": " North Clinic ", "location": " Delhi "}).json()
    diagnostic_test = client.post("/tests/", headers=headers, json={"name": "Blood Panel", "description": None}).json()
    offering = client.post(f"/centres/{centre['id']}/tests/", headers=headers, json={"test_id": diagnostic_test["id"], "price_minor": 49900})
    assert offering.status_code == 201
    assert client.post(f"/centres/{centre['id']}/tests/", headers=headers, json={"test_id": diagnostic_test["id"], "price_minor": 49900}).status_code == 409
    assert client.patch(f"/centres/{centre['id']}/tests/{diagnostic_test['id']}/", headers=headers, json={"price_minor": 59900}).json()["price_minor"] == 59900
    assert client.delete(f"/tests/{diagnostic_test['id']}/", headers=headers).status_code == 204
    assert client.get(f"/centres/{centre['id']}/tests/").json() == []


def test_catalogue_public_filters_pagination_and_validation(client: TestClient) -> None:
    headers = _headers(client, "filters@example.com")
    assert client.post("/centres/", headers=headers, json={"name": "Zulu", "location": "Mumbai"}).status_code == 201
    assert client.post("/centres/", headers=headers, json={"name": "Alpha", "location": "Delhi"}).status_code == 201
    assert [item["name"] for item in client.get("/centres/?location=DELHI").json()["items"]] == ["Alpha"]
    assert [item["name"] for item in client.get("/centres/?limit=1&offset=1").json()["items"]] == ["Zulu"]
    assert client.post("/centres/", headers=headers, json={"name": " ", "location": "Delhi"}).status_code == 422
    assert client.post("/tests/", headers=headers, json={"name": "CBC", "unknown": "field"}).status_code == 422
