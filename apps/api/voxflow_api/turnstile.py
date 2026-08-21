"""Cloudflare Turnstile server-side validation with privacy-safe outputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import uuid

import httpx

from .config import get_settings


SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
VALID_ACTIONS = frozenset({"sign_in", "sign_up"})


@dataclass(frozen=True)
class TurnstileValidation:
    valid: bool
    code: str
    configured: bool


def _safe_error_code(response: dict[str, object]) -> str:
    codes = response.get("error-codes")
    if isinstance(codes, list) and codes and isinstance(codes[0], str):
        return codes[0][:64]
    return "verification_failed"


async def validate_turnstile_token(
    *,
    token: str,
    action: Literal["sign_in", "sign_up"],
    remote_ip: str | None,
) -> TurnstileValidation:
    """Validate one token using Siteverify and return a redacted result only."""

    settings = get_settings()
    if not settings.turnstile_secret_key:
        return TurnstileValidation(valid=False, code="turnstile_not_configured", configured=False)
    if action not in VALID_ACTIONS or not token or len(token) > 2048:
        return TurnstileValidation(valid=False, code="invalid_input", configured=True)

    payload: dict[str, str] = {
        "secret": settings.turnstile_secret_key,
        "response": token,
        "idempotency_key": str(uuid.uuid4()),
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(SITEVERIFY_URL, data=payload)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError):
        return TurnstileValidation(valid=False, code="verification_unavailable", configured=True)

    if not isinstance(result, dict) or result.get("success") is not True:
        return TurnstileValidation(valid=False, code=_safe_error_code(result if isinstance(result, dict) else {}), configured=True)
    if result.get("action") != action:
        return TurnstileValidation(valid=False, code="action_mismatch", configured=True)
    expected_hostname = settings.turnstile_expected_hostname.strip().lower()
    returned_hostname = str(result.get("hostname") or "").strip().lower()
    if expected_hostname and returned_hostname != expected_hostname:
        return TurnstileValidation(valid=False, code="hostname_mismatch", configured=True)
    return TurnstileValidation(valid=True, code="verified", configured=True)
