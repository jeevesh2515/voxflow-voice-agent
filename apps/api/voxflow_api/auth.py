"""Supabase JWT authentication for FastAPI.

Validates Bearer tokens issued by Supabase Auth and exposes the decoded
payload on `request.state.auth`. Routes can read:

    tenant_id = request.state.auth.tenant_id or DEFAULT_TENANT_ID
    user_id   = request.state.auth.user_id

If no valid token is present, `request.state.auth` is an anonymous guest
so the existing query-parameter fallback still works. This lets us roll out
auth without breaking the existing demo/test paths.
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Request

from .config import get_settings


@dataclass
class AuthUser:
    user_id: str
    email: Optional[str] = None
    tenant_id: Optional[str] = None
    role: str = "anon"


# In-memory JWKS cache (refreshes every 5 minutes).
_jwks_cache: dict[str, tuple[dict, float]] = {}


def _fetch_jwks() -> dict:
    s = get_settings()
    url = s.supabase_jwks_url
    if not url:
        return {}

    now = time.time()
    cached_key, cached_at = _jwks_cache.get("keys", ({}, 0.0))
    if cached_key and (now - cached_at) < 300:
        return cached_key

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        _jwks_cache["keys"] = (data, now)
        return data
    except Exception:
        return cached_key or {}


def _verify_token(token: str) -> Optional[AuthUser]:
    s = get_settings()
    if not s.supabase_url or not s.supabase_jwks_url:
        return None

    jwks = _fetch_jwks()
    if not jwks.get("keys"):
        return None

    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception:
        return None

    kid = unverified_header.get("kid")
    key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
    if not key:
        return None

    try:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=f"{s.supabase_url}/auth/v1",
            options={"require": ["exp", "iss", "sub"]},
        )
    except Exception:
        return None

    email = payload.get("email")
    tenant_id = (
        payload.get("user_metadata", {}).get("tenant_id")
        or payload.get("app_metadata", {}).get("tenant_id")
    )
    return AuthUser(
        user_id=str(payload.get("sub", "")),
        email=str(email) if email else None,
        tenant_id=str(tenant_id) if tenant_id else None,
        role=str(payload.get("role", "anon")),
    )


class AuthMiddleware:
    """FastAPI middleware that validates Supabase JWT Bearer tokens."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        auth = AuthUser(user_id="", role="anon")

        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            verified = _verify_token(token)
            if verified:
                auth = verified

        request.state.auth = auth
        await self.app(scope, receive, send)


def get_auth(request: Request) -> AuthUser:
    return getattr(request.state, "auth", AuthUser(user_id="", role="anon"))
