"""Public entry protection endpoints.

No endpoint here creates a workspace, changes tenant access, starts a worker, or
contacts an operational provider. The only external request is Cloudflare's
Turnstile Siteverify validation when it has been explicitly configured.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from ..auth import get_auth
from ..config import get_settings
from ..db import session_scope
from ..services.provisioning import (
    PhoneNumberConflictError,
    TenantSlugConflictError,
    provision_tenant,
)
from ..turnstile import validate_turnstile_token


router = APIRouter(prefix="/api/auth", tags=["public-auth"])


class TurnstileVerifyIn(BaseModel):
    token: str = Field(..., min_length=1, max_length=2048)
    action: Literal["sign_in", "sign_up"]


class SelfServeSignupIn(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=120, description="Full company name")
    email: str = Field(..., min_length=3, max_length=320, description="Admin contact email")
    name: str = Field(default="", max_length=120, description="Admin user full name")
    user_id: str | None = Field(default=None, max_length=128, description="Supabase auth user UUID if available")
    tenant_id: str | None = Field(default=None, max_length=64, description="Optional custom tenant slug")
    phone_number: str | None = Field(default=None, max_length=32, description="Optional phone number")
    agent_name: str = Field(default="Vaani", max_length=64, description="Voice agent persona name")
    default_language: Literal["en", "hi"] = Field(default="en", description="Default voice language")
    plan: Literal["starter", "pro", "enterprise"] = Field(default="pro", description="Subscription plan")
    seed_starter_data: bool = Field(default=True, description="Prepopulate with starter catalog for immediate testing")
    turnstile_token: str | None = Field(default=None, description="Cloudflare Turnstile token")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("a valid email address is required")
        return normalized


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


@router.post("/signup")
async def self_serve_signup(payload: SelfServeSignupIn, request: Request) -> dict[str, Any]:
    """Self-serve customer onboarding creating an isolated tenant and owner membership."""

    settings = get_settings()
    if settings.turnstile_secret_key:
        if not payload.turnstile_token:
            raise HTTPException(status_code=403, detail="turnstile_token_required")
        turnstile_res = await validate_turnstile_token(
            token=payload.turnstile_token,
            action="sign_up",
            remote_ip=_request_ip(request),
        )
        if not turnstile_res.valid:
            raise HTTPException(status_code=403, detail="challenge_verification_failed")

    auth = get_auth(request)
    claimed_user_id = (payload.user_id or "").strip()
    if claimed_user_id and not auth.identity_verified:
        raise HTTPException(status_code=401, detail="verified_identity_required_for_user_id")
    if claimed_user_id and claimed_user_id != auth.user_id:
        raise HTTPException(status_code=403, detail="signup_user_id_mismatch")

    owner_user_id = (
        auth.user_id
        if auth.identity_verified
        else f"pending-signup-{uuid.uuid4().hex}"
    )
    owner_email = auth.email if auth.identity_verified and auth.email else payload.email

    try:
        with session_scope() as db:
            result = provision_tenant(
                db,
                name=payload.company_name,
                owner_user_id=owner_user_id,
                tenant_id=payload.tenant_id,
                owner_email=owner_email,
                agent_name=payload.agent_name,
                default_language=payload.default_language,
                plan=payload.plan,
                phone_number=payload.phone_number,
                seed_starter_data=payload.seed_starter_data,
                invited_by="self_serve_signup",
            )
            return result
    except (PhoneNumberConflictError, TenantSlugConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
