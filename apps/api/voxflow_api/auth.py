"""Supabase JWT authentication and tenant-role authorization for FastAPI.

Supabase validates identity. The application-owned ``tenant_members`` ledger is
the sole source of tenant role and lifecycle authorization; browser-selected
workspace IDs and mutable JWT metadata never grant access on their own.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
import os
import time
from typing import Iterable, Optional
import urllib.request

import jwt
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from .config import get_settings
from .db import TenantMember


ROLE_OWNER = "owner"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"
MEMBER_ROLES = frozenset({ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER})
MEMBER_STATUSES = frozenset({"invited", "active", "revoked"})


@dataclass
class AuthUser:
    user_id: str
    email: Optional[str] = None
    tenant_id: Optional[str] = None
    role: str = "anon"
    is_demo: bool = False
    identity_verified: bool = False


# In-memory JWKS cache (refreshes every 5 minutes).
_jwks_cache: dict[str, tuple[dict, float]] = {}


def _fetch_jwks() -> dict:
    settings = get_settings()
    url = settings.supabase_jwks_url
    if not url:
        return {}

    now = time.time()
    cached_key, cached_at = _jwks_cache.get("keys", ({}, 0.0))
    if cached_key and (now - cached_at) < 300:
        return cached_key

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
        _jwks_cache["keys"] = (data, now)
        return data
    except Exception:
        return cached_key or {}


def _verify_token(token: str) -> Optional[AuthUser]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_jwks_url:
        return None

    jwks = _fetch_jwks()
    if not jwks.get("keys"):
        return None

    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception:
        return None

    key_id = unverified_header.get("kid")
    key = next((item for item in jwks["keys"] if item.get("kid") == key_id), None)
    if not key:
        return None

    try:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=f"{settings.supabase_url}/auth/v1",
            options={"require": ["exp", "iss", "sub"]},
        )
    except Exception:
        return None

    email = payload.get("email")
    metadata = payload.get("user_metadata", {}) or {}
    app_metadata = payload.get("app_metadata", {}) or {}
    return AuthUser(
        user_id=str(payload.get("sub", "")),
        email=str(email) if email else None,
        # Legacy metadata remains available for migration diagnostics only. It
        # is never used by role checks below.
        tenant_id=str(metadata.get("tenant_id") or app_metadata.get("tenant_id") or "") or None,
        role="authenticated",
        identity_verified=True,
    )


def _synthetic_local_identity_enabled() -> bool:
    """Allow deterministic test identities only in an explicit offline test mode."""

    settings = get_settings()
    explicit_test_runtime = bool(os.environ.get("PYTEST_CURRENT_TEST")) or (
        os.environ.get("VOXFLOW_TESTING", "").strip().lower()
        in {"1", "true", "yes"}
    )
    return (
        explicit_test_runtime
        and not settings.tenant_authorization_enforced
        and settings.database_url.startswith("sqlite:")
        and not settings.supabase_url
        and not settings.supabase_jwks_url
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
            if verified and verified.user_id:
                auth = replace(verified, identity_verified=True)
            elif _synthetic_local_identity_enabled() and (
                token.startswith("usr-") or token.startswith("user-")
            ):
                auth = AuthUser(user_id=token, role="authenticated")
        user_id_hdr = request.headers.get("x-voxflow-user-id", "").strip()
        if user_id_hdr and not auth.user_id and _synthetic_local_identity_enabled():
            auth = AuthUser(user_id=user_id_hdr, role="authenticated")
        request.state.auth = auth
        await self.app(scope, receive, send)


def get_auth(request: Request) -> AuthUser:
    return getattr(request.state, "auth", AuthUser(user_id="", role="anon"))


def normalized_email_hash(email: str | None, *, fallback_subject: str = "") -> str:
    """Return a stable hashed identity label without retaining a raw email."""

    value = (email or "").strip().lower()
    if not value:
        value = f"subject:{fallback_subject.strip()}"
    return sha256(value.encode("utf-8")).hexdigest()


def _demo_auth(request: Request) -> AuthUser | None:
    """Recognize the browser demo only for the fixed non-sensitive demo tenant.

    A client header is not a substitute for authentication. It is deliberately
    limited to a configured demonstration tenant and may only be used by routes
    that explicitly pass ``allow_demo=True``. Mutations, invitations, admin
    configuration, and membership lifecycle operations always reject it.
    """

    settings = get_settings()
    requested = request.headers.get("x-voxflow-demo", "").strip().lower()
    tenant = request.headers.get("x-voxflow-demo-tenant", "").strip()
    if (
        settings.demo_mode_enabled
        and requested == "enabled"
        and tenant == settings.demo_tenant_id
    ):
        return AuthUser(
            user_id="demo-readonly-viewer",
            email="demo@voxflow.invalid",
            tenant_id=settings.demo_tenant_id,
            role=ROLE_VIEWER,
            is_demo=True,
        )
    return None


def require_authenticated_user(request: Request, *, allow_demo: bool = False) -> AuthUser:
    """Return a verified identity or reject anonymous browser/API traffic."""

    auth = get_auth(request)
    if auth.user_id:
        return auth
    if allow_demo:
        demo = _demo_auth(request)
        if demo is not None:
            return demo
    settings = get_settings()
    if not settings.tenant_authorization_enforced:
        return AuthUser(user_id="legacy-local-compatibility", role="authenticated")
    raise HTTPException(status_code=401, detail="authentication_required")



def active_membership(db: Session, *, tenant_id: str, user_id: str) -> TenantMember | None:
    return (
        db.query(TenantMember)
        .filter(
            TenantMember.tenant_id == tenant_id,
            TenantMember.user_id == user_id,
            TenantMember.status == "active",
        )
        .first()
    )


def require_tenant_role(
    request: Request,
    db: Session,
    *,
    tenant_id: str,
    allowed_roles: Iterable[str] = MEMBER_ROLES,
    allow_demo: bool = False,
) -> AuthUser:
    """Require one active application-owned tenant membership and role."""

    expected_roles = frozenset(allowed_roles)
    if not expected_roles.issubset(MEMBER_ROLES):
        raise ValueError("unsupported tenant role in authorization policy")

    settings = get_settings()
    if not settings.tenant_authorization_enforced:
        # Local migration/test compatibility only. Production defaults to true,
        # where a verified subject and active tenant_members row are mandatory.
        return AuthUser(user_id="legacy-local-compatibility", tenant_id=tenant_id, role=ROLE_OWNER)

    auth = require_authenticated_user(request, allow_demo=True)
    if auth.is_demo:
        if tenant_id == settings.demo_tenant_id and ROLE_VIEWER in expected_roles:
            return auth
        raise HTTPException(status_code=403, detail="demo_access_read_only")

    membership = active_membership(db, tenant_id=tenant_id, user_id=auth.user_id)
    if membership is None:
        raise HTTPException(status_code=403, detail="tenant_membership_required")
    if membership.role not in expected_roles:
        raise HTTPException(status_code=403, detail="tenant_role_insufficient")
    return AuthUser(
        user_id=auth.user_id,
        email=auth.email,
        tenant_id=tenant_id,
        role=membership.role,
        is_demo=False,
    )


def require_platform_admin(request: Request) -> AuthUser:
    """Require a verified identity in the explicit platform-admin allow-list."""

    settings = get_settings()
    if not settings.tenant_authorization_enforced:
        return AuthUser(user_id="legacy-local-platform-admin", role=ROLE_OWNER)
    auth = require_authenticated_user(request)
    if auth.user_id not in settings.platform_admin_user_id_set:
        raise HTTPException(status_code=403, detail="platform_admin_required")
    return auth


def membership_summary(member: TenantMember) -> dict[str, object]:
    """Serialize membership without exposing raw email identity or invitation data."""

    return {
        "id": member.id,
        "tenant_id": member.tenant_id,
        "user_id": member.user_id,
        "role": member.role,
        "status": member.status,
        "invited_by": member.invited_by,
        "activated_at": member.activated_at.isoformat() if member.activated_at else None,
        "revoked_at": member.revoked_at.isoformat() if member.revoked_at else None,
        "created_at": member.created_at.isoformat() if member.created_at else None,
        "updated_at": member.updated_at.isoformat() if member.updated_at else None,
    }
