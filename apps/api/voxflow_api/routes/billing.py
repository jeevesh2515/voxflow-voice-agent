"""Day 53 tenant-scoped Stripe billing endpoints.

Authorization model
-------------------
Read (``GET /status``) accepts any active member role, including the fixed
read-only demo viewer, because a plan badge is not sensitive.

Write (``POST /checkout``, ``POST /portal``) is **owner-only**. Both start a
flow that can move money or cancel a subscription, so operator and viewer are
rejected with 403 — as is any member of a different tenant, since
``require_tenant_role`` resolves the role from the ``tenant_members`` ledger for
the tenant named in the path.

``POST /api/billing/webhook`` is deliberately unauthenticated: Stripe cannot
present a bearer token. Its trust comes entirely from the HMAC signature over
the raw request body, verified before any field is read. An unverifiable payload
returns 400 and changes nothing.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..auth import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER, require_tenant_role
from ..config import get_settings
from ..db import Tenant, get_session
from ..logging import get_logger
from ..services.billing_service import (
    PLAN_CATALOG,
    BillingConfigurationError,
    WebhookVerificationError,
    create_checkout_session,
    create_customer_portal_session,
    get_billing_status,
    handle_webhook_event,
)


log = get_logger(__name__)

router = APIRouter(prefix="/api/tenants/{tenant_id}/billing", tags=["billing"])
webhook_router = APIRouter(prefix="/api/billing", tags=["billing"])

READ_ROLES = {ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER}

# A redirect target is attacker-influenced input. Only same-origin-ish absolute
# http(s) URLs are accepted so a crafted checkout request cannot turn the
# post-payment redirect into an open redirect to an arbitrary scheme.
_ALLOWED_URL_SCHEMES = ("http://", "https://")


def _validate_redirect_url(value: str, field_name: str) -> str:
    normalized = (value or "").strip()
    if not normalized.startswith(_ALLOWED_URL_SCHEMES):
        raise ValueError(f"{field_name} must be an absolute http(s) URL")
    return normalized


class CheckoutIn(BaseModel):
    plan_tier: Literal["starter", "growth", "enterprise"]
    success_url: str = Field(..., min_length=8, max_length=2048)
    cancel_url: str = Field(..., min_length=8, max_length=2048)

    @field_validator("success_url")
    @classmethod
    def _check_success_url(cls, value: str) -> str:
        return _validate_redirect_url(value, "success_url")

    @field_validator("cancel_url")
    @classmethod
    def _check_cancel_url(cls, value: str) -> str:
        return _validate_redirect_url(value, "cancel_url")


class PortalIn(BaseModel):
    return_url: str | None = Field(default=None, max_length=2048)

    @field_validator("return_url")
    @classmethod
    def _check_return_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return _validate_redirect_url(value, "return_url")


def _require_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
    return tenant


@router.get("/status")
def get_status(
    tenant_id: str,
    request: Request,
    invoice_limit: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Return plan, subscription status, renewal date, and invoice history."""

    _require_tenant(db, tenant_id)
    require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles=READ_ROLES, allow_demo=True)
    payload = get_billing_status(db, tenant_id, invoice_limit=invoice_limit)
    payload["catalog"] = {
        tier: {
            "name": spec["name"],
            "amount_pence": spec["amount_pence"],
            "voice_lines": spec["voice_lines"],
            "included_minutes": spec["included_minutes"],
        }
        for tier, spec in PLAN_CATALOG.items()
    }
    return payload


@router.post("/checkout")
def post_checkout(
    tenant_id: str,
    payload: CheckoutIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Start a Stripe Checkout Session. Owner-only — it can start a charge."""

    _require_tenant(db, tenant_id)
    actor = require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
    try:
        session_payload = create_checkout_session(
            db,
            tenant_id=tenant_id,
            plan_tier=payload.plan_tier,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
            user_email=actor.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"ok": True, "checkout": session_payload}


@router.post("/portal")
def post_portal(
    tenant_id: str,
    payload: PortalIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Start a Stripe Customer Portal session. Owner-only — it can cancel."""

    _require_tenant(db, tenant_id)
    require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
    try:
        session_payload = create_customer_portal_session(db, tenant_id=tenant_id, return_url=payload.return_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except BillingConfigurationError as exc:
        # 409 rather than 500: the tenant simply has no Stripe customer yet, so
        # the dashboard should send them through checkout first.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"ok": True, "portal": session_payload}


@webhook_router.post("/webhook")
async def post_webhook(request: Request, db: Session = Depends(get_session)) -> dict[str, Any]:
    """Ingest one Stripe webhook event.

    The raw body is read before parsing because the signature covers the exact
    bytes Stripe sent; re-serialising a parsed dict would break verification.
    """

    payload_bytes = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        result = handle_webhook_event(db, payload_bytes, sig_header)
    except WebhookVerificationError as exc:
        # Fail closed. The reason code is a fixed enum, never payload content.
        log.warning("billing.webhook_rejected reason=%s", str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"webhook_rejected:{exc}") from exc
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    db.commit()
    return {"ok": True, **result}


@webhook_router.get("/config")
def get_public_billing_config() -> dict[str, Any]:
    """Public, non-secret billing configuration for the pricing page."""

    settings = get_settings()
    return {
        "ok": True,
        "billing_mode": "live" if settings.stripe_live_mode else "sandbox",
        "publishable_key": settings.stripe_publishable_key or None,
        "currency": "gbp",
        "trial_period_days": settings.billing_trial_period_days,
        "catalog": {
            tier: {
                "name": spec["name"],
                "amount_pence": spec["amount_pence"],
                "voice_lines": spec["voice_lines"],
                "included_minutes": spec["included_minutes"],
            }
            for tier, spec in PLAN_CATALOG.items()
        },
    }
