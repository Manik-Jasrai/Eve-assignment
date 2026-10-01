"""HTTP booking tests backed by the in-memory database mock."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _headers(client: TestClient, email: str) -> dict[str, str]:
    credentials = {"email": email, "password": "correct-horse-battery"}
    assert client.post("/auth/signup/", json=credentials).status_code == 201
    token = client.post("/auth/login/", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _offering(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    centre = client.post("/centres/", headers=headers, json={"name": "Booking Centre", "location": "Delhi"}).json()
    test = client.post("/tests/", headers=headers, json={"name": "Booking Test"}).json()
    return client.post(f"/centres/{centre['id']}/tests/", headers=headers, json={"test_id": test["id"], "price_minor": 49900}).json()


def test_booking_snapshots_price_and_hides_other_users_bookings(client: TestClient) -> None:
    owner = _headers(client, "owner@example.com")
    offering = _offering(client, owner)
    appointment = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    created = client.post("/bookings/", headers=owner, json={"centre_test_id": offering["id"], "appointment_at": appointment})
    assert created.status_code == 201
    booking = created.json()
    assert booking["status"] == "PENDING"
    assert booking["amount_minor"] == 49900
    assert client.patch(f"/centres/{offering['centre_id']}/tests/{offering['test_id']}/", headers=owner, json={"price_minor": 59900}).status_code == 200
    assert client.get(f"/bookings/{booking['id']}/", headers=owner).json()["amount_minor"] == 49900
    assert client.get(f"/bookings/{booking['id']}/", headers=_headers(client, "other@example.com")).status_code == 404


def test_booking_rejects_invalid_time_and_inactive_offering(client: TestClient) -> None:
    headers = _headers(client, "time@example.com")
    offering = _offering(client, headers)
    assert client.post("/bookings/", headers=headers, json={"centre_test_id": offering["id"], "appointment_at": "2030-01-01T10:00:00"}).status_code == 422
    assert client.post("/bookings/", headers=headers, json={"centre_test_id": offering["id"], "appointment_at": (datetime.now(UTC) - timedelta(days=1)).isoformat()}).status_code == 422
    assert client.delete(f"/centres/{offering['centre_id']}/tests/{offering['test_id']}/", headers=headers).status_code == 204
    assert client.post("/bookings/", headers=headers, json={"centre_test_id": offering["id"], "appointment_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()}).status_code == 409
