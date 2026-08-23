"""Tests for Amazon Connect AWS Lambda integration routes."""

from __future__ import annotations

import hashlib
import hmac
import time
import pytest
from fastapi.testclient import TestClient

from voxflow_api.config import get_settings
from voxflow_api.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_connect_turn_execution(client):
    payload = {
        "contact_id": "cnt-12345",
        "customer_phone": "+919876543210",
        "system_phone": "+1800123456",
        "user_text": "नमस्ते, क्या मेरा ऑर्डर डिस्पैच हो गया?",
        "language": "hi",
    }
    r = client.post("/api/connect/turn", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["contact_id"] == "cnt-12345"
    assert "agent_reply" in data
    assert isinstance(data["escalate"], bool)
    assert isinstance(data["end_call"], bool)
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], float)
    assert data["latency_ms"] >= 0.0


def test_connect_turn_with_signature_verification(monkeypatch, client):
    s = get_settings()
    monkeypatch.setattr(s, "connect_lambda_secret", "test_secret_123", raising=False)

    payload = {
        "contact_id": "cnt-signed-1",
        "customer_phone": "+919876543210",
        "system_phone": "+1800123456",
        "user_text": "Check status",
        "language": "en",
    }

    # Unsigned request should be rejected (403)
    r_unauth = client.post("/api/connect/turn", json=payload)
    assert r_unauth.status_code == 403

    # Correctly signed request should succeed (200)
    ts = str(time.time())
    sig = hmac.new(
        b"test_secret_123",
        f"{ts}:/api/connect/turn".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "x-voxflow-signature": sig,
        "x-voxflow-timestamp": ts,
    }
    r_auth = client.post("/api/connect/turn", json=payload, headers=headers)
    assert r_auth.status_code == 200
    assert r_auth.json()["contact_id"] == "cnt-signed-1"


def test_connect_end_call(client):
    payload = {
        "contact_id": "cnt-end-test",
        "outcome": "resolved",
    }
    r = client.post("/api/connect/end", json=payload)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["contact_id"] == "cnt-end-test"
