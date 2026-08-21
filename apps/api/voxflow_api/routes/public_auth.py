"""Public entry protection endpoints.

No endpoint here creates a workspace, changes tenant access, starts a worker, or
contacts an operational provider. The only external request is Cloudflare's
Turnstile Siteverify validation when it has been explicitly configured.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..turnstile import validate_turnstile_token


router = APIRouter(prefix="/api/auth", tags=["public-auth"])


class TurnstileVerifyIn(BaseModel):
    token: str = Field(..., min_length=1, max_length=2048)
    action: Literal["sign_in", "sign_up"]


def _request_ip(request: Request) -> str | None:
    """Read a best-effort client address without retaining or logging it."""

    cloudflare_ip = request.headers.get("cf-connecting-ip", "").strip()
    if cloudflare_ip:
        return cloudflare_ip
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else None


@router.post("/verify-turnstile")
async def verify_turnstile(payload: TurnstileVerifyIn, request: Request) -> dict[str, object]:
    """Validate a short-lived single-use challenge token at the backend only."""

    result = await validate_turnstile_token(
        token=payload.token,
        action=payload.action,
        remote_ip=_request_ip(request),
    )
    if not result.configured:
        raise HTTPException(status_code=503, detail="turnstile_not_configured")
    if not result.valid:
        raise HTTPException(status_code=403, detail="challenge_verification_failed")
    return {"ok": True, "action": payload.action, "verification": "server_validated"}
