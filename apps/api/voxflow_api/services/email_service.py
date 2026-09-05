"""Resend transactional email service.

Dispatches transactional emails via Resend's REST API.
When RESEND_API_KEY is not configured or in sandbox mode, operations
safely record a simulated dispatch without raising network errors.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(
    to: str | list[str],
    subject: str,
    html: str,
    text: str | None = None,
    from_email: str | None = None,
) -> dict[str, Any]:
    """Send a transactional email via Resend REST API."""
    settings = get_settings()
    api_key = (settings.resend_api_key or "").strip()
    sender = (from_email or settings.resend_from_email or "VoxFlow <onboarding@resend.dev>").strip()

    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        return {"status": "skipped", "reason": "no_recipients"}

    if not api_key:
        logger.info(
            "Resend API key not configured; simulating email dispatch to %s (subject: %s)",
            recipients,
            subject,
        )
        return {
            "id": "mock_sandbox_email_id",
            "status": "sandbox_mode",
            "to": recipients,
            "subject": subject,
        }

    payload: dict[str, Any] = {
        "from": sender,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(RESEND_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            email_id = data.get("id", "sent")
            logger.info("Resend email sent successfully: id=%s to=%s", email_id, recipients)
            return {
                "id": email_id,
                "status": "delivered",
                "to": recipients,
                "subject": subject,
            }
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text
            logger.error("Resend API error %s: %s", exc.response.status_code, error_body)
            return {
                "status": "failed",
                "error": f"HTTP {exc.response.status_code}: {error_body}",
                "to": recipients,
            }
        except Exception as exc:
            logger.error("Resend dispatch network error: %s", exc)
            return {
                "status": "failed",
                "error": str(exc),
                "to": recipients,
            }
