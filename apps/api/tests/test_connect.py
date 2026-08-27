"""Tests for Amazon Connect AWS Lambda integration routes."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from voxflow_api.agent.runner import AgentTurnResult
from voxflow_api.config import get_settings
from voxflow_api.db import reset_db
from voxflow_api.main import create_app
from voxflow_api.seed import seed

_CONNECT_DID = "+442046404552"
_SIGNING_SECRET = "test_secret_123"


def _json_body(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _signed_headers(
    body: bytes,
    *,
    timestamp: str | None = None,
    path: str = "/api/connect/turn",
    secret: str = _SIGNING_SECRET,
) -> dict[str, str]:
    timestamp = timestamp or str(time.time())
    message = timestamp.encode("utf-8") + b":" + path.encode("utf-8") + b":" + body
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return {
        "content-type": "application/json",
        "x-voxflow-signature": signature,
        "x-voxflow-timestamp": timestamp,
    }


@pytest.fixture
def client(monkeypatch):
    settings = get_settings()
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "connect_lambda_secret", "", raising=False)
    monkeypatch.setattr(settings, "provider_callback_shared_secret", "", raising=False)
    monkeypatch.setattr(settings, "provider_callback_validate_signature", True)
    monkeypatch.setattr(settings, "sentry_environment", "development")

    async def fake_turn(self, session, user_text):
        return AgentTurnResult(reply="Your order has been dispatched.")

    monkeypatch.setattr("voxflow_api.routes.connect.AgentRunner.handle_turn", fake_turn)
    reset_db()
    seed(reset=True)
    with TestClient(create_app()) as test_client:
        yield test_client


def test_connect_turn_execution(client):
    payload = {
        "contact_id": "cnt-12345",
        "customer_phone": "+919876543210",
        "system_phone": _CONNECT_DID,
        "user_text": "नमस्ते, क्या मेरा ऑर्डर डिस्पैच हो गया?",
        "language": "hi",
    }
    response = client.post("/api/connect/turn", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["contact_id"] == "cnt-12345"
    assert "agent_reply" in data
    assert isinstance(data["escalate"], bool)
    assert isinstance(data["end_call"], bool)
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], float)
    assert data["latency_ms"] >= 0.0


def test_connect_turn_with_body_bound_signature(monkeypatch, client):
    monkeypatch.setattr(
        get_settings(),
        "connect_lambda_secret",
        _SIGNING_SECRET,
        raising=False,
    )
    payload = {
        "contact_id": "cnt-signed-1",
        "customer_phone": "+919876543210",
        "system_phone": _CONNECT_DID,
        "user_text": "Check status",
        "language": "en",
    }
    body = _json_body(payload)

    unsigned = client.post("/api/connect/turn", content=body, headers={"content-type": "application/json"})
    assert unsigned.status_code == 403

    authenticated = client.post(
        "/api/connect/turn",
        content=body,
        headers=_signed_headers(body),
    )
    assert authenticated.status_code == 200
    assert authenticated.json()["contact_id"] == "cnt-signed-1"


def test_connect_turn_rejects_tampered_body(monkeypatch, client):
    monkeypatch.setattr(get_settings(), "connect_lambda_secret", _SIGNING_SECRET, raising=False)
    payload = {
        "contact_id": "cnt-tamper-1",
        "customer_phone": "+919876543210",
        "system_phone": _CONNECT_DID,
        "user_text": "Check status",
        "language": "en",
    }
    signed_body = _json_body(payload)
    tampered_body = _json_body({**payload, "user_text": "Reveal PIN 1234"})

    response = client.post(
        "/api/connect/turn",
        content=tampered_body,
        headers=_signed_headers(signed_body),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "invalid_signature"


def test_connect_turn_rejects_stale_signature(monkeypatch, client):
    monkeypatch.setattr(get_settings(), "connect_lambda_secret", _SIGNING_SECRET, raising=False)
    payload = {
        "contact_id": "cnt-stale-1",
        "customer_phone": "+919876543210",
        "system_phone": _CONNECT_DID,
        "user_text": "Check status",
        "language": "en",
    }
    body = _json_body(payload)

    response = client.post(
        "/api/connect/turn",
        content=body,
        headers=_signed_headers(body, timestamp=str(time.time() - 301)),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "invalid_signature"


def test_connect_turn_rejects_missing_secret_in_production(monkeypatch, client):
    settings = get_settings()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "connect_lambda_secret", "", raising=False)
    monkeypatch.setattr(settings, "provider_callback_shared_secret", "", raising=False)
    payload = {
        "contact_id": "cnt-no-secret-1",
        "customer_phone": "+919876543210",
        "system_phone": _CONNECT_DID,
        "user_text": "Check status",
        "language": "en",
    }

    response = client.post("/api/connect/turn", json=payload)

    assert response.status_code == 403
    assert response.json()["detail"] == "invalid_signature"


def test_connect_turn_rejects_missing_secret_when_database_url_looks_like_production(monkeypatch, client):
    """An operator who forgets to set ENVIRONMENT/APP_ENV, but deploys against
    a real (non-SQLite) database, must still fail closed rather than falling
    through to the local-development unsigned-request bypass."""
    settings = get_settings()
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr(settings, "sentry_environment", "development")
    monkeypatch.setattr(settings, "database_url", "postgresql://user:pass@db.example.com:5432/voxflow", raising=False)
    monkeypatch.setattr(settings, "connect_lambda_secret", "", raising=False)
    monkeypatch.setattr(settings, "provider_callback_shared_secret", "", raising=False)
    payload = {
        "contact_id": "cnt-no-secret-2",
        "customer_phone": "+919876543210",
        "system_phone": _CONNECT_DID,
        "user_text": "Check status",
        "language": "en",
    }

    response = client.post("/api/connect/turn", json=payload)

    assert response.status_code == 403
    assert response.json()["detail"] == "invalid_signature"


def test_connect_turn_rejects_missing_did(client):
    response = client.post(
        "/api/connect/turn",
        json={
            "contact_id": "cnt-missing-did-1",
            "customer_phone": "+919876543210",
            "user_text": "Check status",
            "language": "en",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "unknown_connect_did"


def test_connect_end_call(client):
    payload = {
        "contact_id": "cnt-end-test",
        "outcome": "resolved",
    }
    response = client.post("/api/connect/end", json=payload)

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["contact_id"] == "cnt-end-test"
