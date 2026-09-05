"""Tests for Resend transactional email service."""

from __future__ import annotations

import pytest
import respx

from voxflow_api.config import get_settings
from voxflow_api.services.email_service import RESEND_API_URL, send_email


@pytest.mark.asyncio
async def test_send_email_sandbox_mode_when_no_api_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "resend_api_key", "")
    result = await send_email(
        to="test@example.com",
        subject="Welcome to VoxFlow",
        html="<p>Welcome!</p>",
    )
    assert result["status"] == "sandbox_mode"
    assert result["id"] == "mock_sandbox_email_id"
    assert result["to"] == ["test@example.com"]


@pytest.mark.asyncio
async def test_send_email_no_recipients():
    result = await send_email(
        to=[],
        subject="No one",
        html="<p>Empty</p>",
    )
    assert result["status"] == "skipped"


@pytest.mark.asyncio
@respx.mock
async def test_send_email_success_with_api_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "resend_api_key", "re_test_key_123")
    monkeypatch.setattr(get_settings(), "resend_from_email", "VoxFlow <hello@voxflow.ai>")

    route = respx.post(RESEND_API_URL).respond(
        status_code=200,
        json={"id": "email_resend_999"},
    )

    result = await send_email(
        to="founder@startup.com",
        subject="Weekly Report",
        html="<p>Here is your report</p>",
        text="Here is your report",
    )

    assert route.called
    assert result["status"] == "delivered"
    assert result["id"] == "email_resend_999"

    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer re_test_key_123"


@pytest.mark.asyncio
@respx.mock
async def test_send_email_api_error(monkeypatch):
    monkeypatch.setattr(get_settings(), "resend_api_key", "re_test_key_123")

    respx.post(RESEND_API_URL).respond(
        status_code=422,
        json={"message": "Invalid email address"},
    )

    result = await send_email(
        to="bad-email",
        subject="Test",
        html="<p>Test</p>",
    )

    assert result["status"] == "failed"
    assert "422" in result["error"]
