"""Public protection and privacy-scrubbed monitoring tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from voxflow_api import turnstile
from voxflow_api.config import get_settings
from voxflow_api.main import create_app
from voxflow_api.monitoring import scrub_sentry_event, scrub_value
from voxflow_api.turnstile import TurnstileValidation


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_turnstile_endpoint_fails_closed_when_public_widget_is_configured_without_secret(client):
    response = client.post("/api/auth/verify-turnstile", json={"token": "test-token", "action": "sign_in"})
    assert response.status_code == 503
    assert response.json()["detail"] == "turnstile_not_configured"


def test_turnstile_endpoint_only_accepts_server_validated_result(monkeypatch):
    async def valid(*, token, action, remote_ip):
        assert token == "challenge-token"
        assert action == "sign_up"
        return TurnstileValidation(valid=True, code="verified", configured=True)

    monkeypatch.setattr("voxflow_api.routes.public_auth.validate_turnstile_token", valid)
    with TestClient(create_app()) as test_client:
        response = test_client.post("/api/auth/verify-turnstile", json={"token": "challenge-token", "action": "sign_up"})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "action": "sign_up", "verification": "server_validated"}


def test_turnstile_validator_rejects_missing_or_oversized_tokens_without_network(monkeypatch):
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "secret")
    get_settings.cache_clear()
    import asyncio

    missing = asyncio.run(turnstile.validate_turnstile_token(token="", action="sign_in", remote_ip=None))
    oversized = asyncio.run(turnstile.validate_turnstile_token(token="x" * 2049, action="sign_in", remote_ip=None))
    assert missing.valid is False and missing.code == "invalid_input"
    assert oversized.valid is False and oversized.code == "invalid_input"
    get_settings.cache_clear()


def test_monitoring_scrubber_removes_direct_identifiers_and_request_content():
    event = {
        "request": {
            "url": "https://example.test/api?phone=+919876543210",
            "headers": {"Authorization": "Bearer secret"},
            "data": {"transcript": "hello", "email": "person@example.test"},
            "cookies": {"session": "secret"},
        },
        "user": {"email": "person@example.test", "ip_address": "203.0.113.5"},
        "extra": {"caller_phone": "+919876543210", "note": "private details"},
        "message": "Contact person@example.test at +919876543210",
    }
    scrubbed = scrub_sentry_event(event)
    assert scrubbed["request"]["url"] == "[redacted-url]"
    assert scrubbed["request"]["headers"] == {"redacted": "[redacted]"}
    assert "user" not in scrubbed and "extra" not in scrubbed
    assert "person@example.test" not in str(scrubbed)
    assert "+919876543210" not in str(scrubbed)
    assert scrub_value({"password": "x", "nested": ["person@example.test"]}) == {"password": "[redacted]", "nested": ["[redacted-email]"]}
