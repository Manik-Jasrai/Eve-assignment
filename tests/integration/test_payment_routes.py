"""HTTP tests for payment and webhook routes."""
from datetime import UTC, datetime, timedelta
from fastapi.testclient import TestClient
from app.core.config import get_settings

def _headers(client: TestClient) -> dict[str, str]:
    credentials = {"email": "pay@example.com", "password": "correct-horse-battery"}
    assert client.post("/auth/signup/", json=credentials).status_code == 201
    token = client.post("/auth/login/", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def _booking(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    centre = client.post("/centres/", headers=headers, json={"name":"Pay Centre","location":"Delhi"}).json()
    test = client.post("/tests/", headers=headers, json={"name":"Pay Test"}).json()
    offering = client.post(f"/centres/{centre['id']}/tests/", headers=headers, json={"test_id":test["id"],"price_minor":49900}).json()
    return client.post("/bookings/", headers=headers, json={"centre_test_id":offering["id"],"appointment_at":(datetime.now(UTC)+timedelta(days=1)).isoformat()}).json()

def test_payment_finalizes_and_replays(client: TestClient) -> None:
    headers = _headers(client); booking = _booking(client, headers)
    first = client.post("/payments/", headers=headers, json={"booking_id":booking["id"],"simulate_status":"SUCCESS"})
    assert first.status_code == 201 and first.json()["status"] == "SUCCESS"
    assert client.post("/payments/", headers=headers, json={"booking_id":booking["id"],"simulate_status":"SUCCESS"}).status_code == 200
    assert client.post("/payments/", headers=headers, json={"booking_id":booking["id"],"simulate_status":"FAILED"}).status_code == 409

def test_webhook_secret_deduplication_and_mismatch(client: TestClient) -> None:
    headers = _headers(client); booking = _booking(client, headers)
    payment = client.post("/payments/", headers=headers, json={"booking_id":booking["id"],"simulate_status":"SUCCESS"}).json()
    body = {"event_id":"evt-1","payment_id":payment["id"],"status":"SUCCESS","amount_minor":49900,"currency":"INR"}
    assert client.post("/payments/webhook/", json=body).status_code == 401
    secret = get_settings().mock_webhook_secret.get_secret_value()
    assert client.post("/payments/webhook/", headers={"X-Webhook-Secret":secret}, json=body).json()["disposition"] == "NOOP"
    assert client.post("/payments/webhook/", headers={"X-Webhook-Secret":secret}, json=body).json()["disposition"] == "DUPLICATE"
    body["amount_minor"] = 1
    assert client.post("/payments/webhook/", headers={"X-Webhook-Secret":secret}, json=body).status_code == 409
