"""HTTP tests for payment and webhook routes."""
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.config import get_settings


def _headers(client: TestClient) -> dict[str, str]:
    credentials = {"email": "pay@example.com", "password": "correct-horse-battery"}
    assert client.post("/auth/signup/", json=credentials).status_code == 201
    token = client.post("/auth/login/", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _booking(client: TestClient, headers: dict[str, str], suffix: str = "one") -> dict[str, object]:
    centre = client.post(
        "/centres/",
        headers=headers,
        json={"name": f"Pay Centre {suffix}", "location": "Delhi"},
    ).json()
    test = client.post("/tests/", headers=headers, json={"name": f"Pay Test {suffix}"}).json()
    offering = client.post(
        f"/centres/{centre['id']}/tests/",
        headers=headers,
        json={"test_id": test["id"], "price_minor": 49900},
    ).json()
    return client.post(
        "/bookings/",
        headers=headers,
        json={
            "centre_test_id": offering["id"],
            "appointment_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    ).json()


def _payment(client: TestClient, headers: dict[str, str], booking: dict[str, object]) -> dict[str, object]:
    response = client.post("/payments/", headers=headers, json={"booking_id": booking["id"]})
    assert response.status_code == 201
    return response.json()


def _webhook_headers() -> dict[str, str]:
    return {"X-Webhook-Secret": get_settings().mock_webhook_secret.get_secret_value()}


def _webhook_body(payment: dict[str, object], status: str, event_id: str = "evt-1") -> dict[str, object]:
    return {
        "event_id": event_id,
        "payment_id": payment["id"],
        "status": status,
        "amount_minor": payment["amount_minor"],
        "currency": payment["currency"],
    }


def test_payment_creation_is_pending_and_idempotent(client: TestClient) -> None:
    headers = _headers(client)
    booking = _booking(client, headers)

    first = client.post("/payments/", headers=headers, json={"booking_id": booking["id"]})
    replay = client.post("/payments/", headers=headers, json={"booking_id": booking["id"]})

    assert first.status_code == 201
    assert first.json()["status"] == "PENDING"
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert client.get(f"/bookings/{booking['id']}/", headers=headers).json()["status"] == "PENDING"
    assert client.post(
        "/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "simulate_status": "SUCCESS"},
    ).status_code == 422


def test_webhook_applies_success_and_failed_results(client: TestClient) -> None:
    headers = _headers(client)
    webhook_headers = _webhook_headers()
    success_booking = _booking(client, headers, "success")
    failed_booking = _booking(client, headers, "failed")
    success_payment = _payment(client, headers, success_booking)
    failed_payment = _payment(client, headers, failed_booking)

    success = client.post(
        "/payments/webhook/",
        headers=webhook_headers,
        json=_webhook_body(success_payment, "SUCCESS", "shared-event-id"),
    )
    failed = client.post(
        "/payments/webhook/",
        headers=webhook_headers,
        json=_webhook_body(failed_payment, "FAILED", "shared-event-id"),
    )

    assert success.status_code == 200
    assert success.json()["disposition"] == "APPLIED"
    assert failed.status_code == 200
    assert failed.json()["disposition"] == "APPLIED"
    assert client.get(f"/payments/{success_payment['id']}/", headers=headers).json()["status"] == "SUCCESS"
    assert client.get(f"/bookings/{success_booking['id']}/", headers=headers).json()["status"] == "CONFIRMED"
    assert client.get(f"/payments/{failed_payment['id']}/", headers=headers).json()["status"] == "FAILED"
    assert client.get(f"/bookings/{failed_booking['id']}/", headers=headers).json()["status"] == "FAILED"


def test_webhook_deduplicates_business_payload_not_event_id(client: TestClient) -> None:
    headers = _headers(client)
    booking = _booking(client, headers)
    payment = _payment(client, headers, booking)
    first_body = _webhook_body(payment, "SUCCESS", "evt-first")
    replay_body = _webhook_body(payment, "SUCCESS", "evt-reused")

    assert client.post("/payments/webhook/", headers=_webhook_headers(), json=first_body).json()["disposition"] == "APPLIED"
    replay = client.post("/payments/webhook/", headers=_webhook_headers(), json=replay_body)

    assert replay.status_code == 200
    assert replay.json()["disposition"] == "DUPLICATE"


def test_webhook_rejects_unauthorized_invalid_and_contradictory_updates(client: TestClient) -> None:
    headers = _headers(client)
    booking = _booking(client, headers)
    payment = _payment(client, headers, booking)
    body = _webhook_body(payment, "SUCCESS")

    assert client.post("/payments/webhook/", json=body).status_code == 401
    pending_body = {**body, "status": "PENDING"}
    assert client.post("/payments/webhook/", headers=_webhook_headers(), json=pending_body).status_code == 422
    invalid_money = {**body, "amount_minor": 1}
    assert client.post("/payments/webhook/", headers=_webhook_headers(), json=invalid_money).status_code == 422
    unknown_payment = {**body, "payment_id": "11111111-1111-4111-8111-111111111111"}
    assert client.post("/payments/webhook/", headers=_webhook_headers(), json=unknown_payment).status_code == 404
    assert client.post("/payments/webhook/", headers=_webhook_headers(), json=body).status_code == 200
    contradictory = {**body, "event_id": "evt-2", "status": "FAILED"}
    assert client.post("/payments/webhook/", headers=_webhook_headers(), json=contradictory).status_code == 409
