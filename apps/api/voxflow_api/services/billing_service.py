"""Stripe billing lifecycle — checkout, customer portal, and webhook ingestion.

Design constraints
------------------
**No secrets in the repository.** Every credential is resolved from the
environment through ``config.Settings``. Nothing here has a hardcoded fallback
key.

**Fail-closed webhook verification.** ``handle_webhook_event`` verifies the
signature before it reads a single field out of the payload. An unsigned,
mis-signed, stale, or malformed payload raises ``WebhookVerificationError`` and
the route turns that into an HTTP 400. There is no code path that applies an
unverified event.

**Sandbox mode instead of a network stub.** When ``STRIPE_SECRET_KEY`` is unset
the service never contacts Stripe: checkout and portal sessions return
deterministic local URLs, and webhooks are verified with an HMAC-SHA256 over the
same ``STRIPE_WEBHOOK_SECRET``, using Stripe's own ``t=...,v1=...`` header
format. This keeps the whole lifecycle exercisable offline *without* weakening
verification — a blank webhook secret is rejected in both modes.

**Tenant-scoped writes only.** Every mutation resolves its tenant from the
event's own ``client_reference_id``/``metadata``/``customer`` fields and writes
to that tenant row alone. No event can move another tenant's subscription.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import Tenant, TenantBillingInvoice
from ..logging import get_logger


log = get_logger(__name__)


PLAN_TIERS = ("starter", "growth", "enterprise")

# Inline price data for sandbox checkout, and the source of truth for the
# publicly advertised GBP pricing. Amounts are in pence.
PLAN_CATALOG: dict[str, dict[str, Any]] = {
    "starter": {
        "name": "VoxFlow Starter",
        "amount_pence": 4900,
        "voice_lines": 1,
        "included_minutes": 500,
    },
    "growth": {
        "name": "VoxFlow Growth",
        "amount_pence": 14900,
        "voice_lines": 3,
        "included_minutes": 2500,
    },
    "enterprise": {
        "name": "VoxFlow Enterprise",
        "amount_pence": 39900,
        "voice_lines": 0,  # 0 == unlimited
        "included_minutes": 0,  # 0 == unmetered
    },
}

SUBSCRIPTION_STATUSES = ("trialing", "active", "past_due", "canceled", "incomplete")

# Signature tolerance, mirroring Stripe's own default.
WEBHOOK_MAX_AGE_SECONDS = 300

HANDLED_EVENT_TYPES = (
    "checkout.session.completed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
)


class BillingConfigurationError(RuntimeError):
    """The requested billing operation is not configured on this deployment."""


class WebhookVerificationError(RuntimeError):
    """The webhook payload could not be cryptographically verified."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stripe_module():
    """Import the Stripe SDK lazily so the package stays an optional dependency.

    The service only needs it in live mode. Importing at module scope would make
    the whole API fail to start on a deployment that has not installed it yet and
    is not billing anyone.
    """

    try:
        import stripe  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:  # pragma: no cover - live-mode only
        raise BillingConfigurationError(
            "STRIPE_SECRET_KEY is configured but the 'stripe' package is not "
            "installed. Fix: pip install -r requirements.txt"
        ) from exc
    stripe.api_key = get_settings().stripe_secret_key
    return stripe


def is_live_mode() -> bool:
    """Whether this process talks to the real Stripe API."""

    return get_settings().stripe_live_mode


def _from_unix(value: Any) -> datetime | None:
    if value in (None, "", 0):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _require_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant_not_found")
    return tenant


def _validate_plan_tier(plan_tier: str) -> str:
    normalized = (plan_tier or "").strip().lower()
    if normalized not in PLAN_TIERS:
        raise ValueError(f"invalid_plan_tier:{plan_tier}")
    return normalized


# ---------- Checkout ----------


def create_checkout_session(
    db: Session,
    tenant_id: str,
    plan_tier: str,
    success_url: str,
    cancel_url: str,
    user_email: str | None = None,
) -> dict[str, Any]:
    """Create a Stripe Checkout Session for one tenant's subscription upgrade.

    ``client_reference_id`` and ``metadata.tenant_id`` both carry the tenant, so
    the completion webhook can resolve it without trusting anything the browser
    sends back.
    """

    tenant = _require_tenant(db, tenant_id)
    tier = _validate_plan_tier(plan_tier)
    settings = get_settings()
    price_id = settings.stripe_price_id(tier)

    metadata = {"tenant_id": tenant_id, "plan_tier": tier}

    if not settings.stripe_live_mode:
        # Sandbox: no network call, no session object on Stripe's side. The URL
        # is obviously local so it can never be mistaken for a real payment page.
        session_id = f"cs_sandbox_{tenant_id}_{tier}_{int(time.time())}"
        log.info("billing.checkout_session_sandbox tenant_id=%s plan_tier=%s", tenant_id, tier)
        return {
            "mode": "sandbox",
            "session_id": session_id,
            "checkout_url": f"{success_url}{'&' if '?' in success_url else '?'}sandbox_session={session_id}",
            "plan_tier": tier,
            "price_id": price_id or None,
            "amount_pence": PLAN_CATALOG[tier]["amount_pence"],
            "currency": "gbp",
            "client_reference_id": tenant_id,
            "metadata": metadata,
            "publishable_key": settings.stripe_publishable_key or None,
        }

    stripe = _stripe_module()
    if price_id:
        line_items = [{"price": price_id, "quantity": 1}]
    else:
        # A live key with no configured price ID still works via inline price
        # data, so a partially configured deployment degrades to a correct
        # charge rather than a 500.
        line_items = [
            {
                "quantity": 1,
                "price_data": {
                    "currency": "gbp",
                    "unit_amount": PLAN_CATALOG[tier]["amount_pence"],
                    "recurring": {"interval": "month"},
                    "product_data": {"name": PLAN_CATALOG[tier]["name"]},
                },
            }
        ]

    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": line_items,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": tenant_id,
        "metadata": metadata,
        "subscription_data": {"metadata": metadata},
    }
    if settings.billing_trial_period_days > 0 and not tenant.stripe_subscription_id:
        params["subscription_data"]["trial_period_days"] = settings.billing_trial_period_days
    if tenant.stripe_customer_id:
        params["customer"] = tenant.stripe_customer_id
    elif user_email:
        params["customer_email"] = user_email

    session = stripe.checkout.Session.create(**params)
    log.info("billing.checkout_session_created tenant_id=%s plan_tier=%s", tenant_id, tier)
    session_id = getattr(session, "id", None) or (session.get("id") if isinstance(session, dict) else None)
    checkout_url = getattr(session, "url", None) or (session.get("url") if isinstance(session, dict) else None)
    return {
        "mode": "live",
        "session_id": session_id,
        "checkout_url": checkout_url,
        "plan_tier": tier,
        "price_id": price_id or None,
        "amount_pence": PLAN_CATALOG[tier]["amount_pence"],
        "currency": "gbp",
        "client_reference_id": tenant_id,
        "metadata": metadata,
        "publishable_key": settings.stripe_publishable_key or None,
    }


# ---------- Customer portal ----------


def create_customer_portal_session(
    db: Session,
    tenant_id: str,
    return_url: str | None = None,
) -> dict[str, Any]:
    """Create a Stripe Customer Portal session for payment methods and receipts.

    The portal is where a customer updates a card, downloads a VAT receipt, or
    cancels. Delegating it to Stripe means no card data ever reaches this app.
    """

    tenant = _require_tenant(db, tenant_id)
    settings = get_settings()
    destination = (return_url or settings.billing_portal_return_url).strip()

    if not tenant.stripe_customer_id:
        raise BillingConfigurationError("no_stripe_customer_for_tenant")

    if not settings.stripe_live_mode:
        log.info("billing.portal_session_sandbox tenant_id=%s", tenant_id)
        return {
            "mode": "sandbox",
            "portal_url": f"{destination}{'&' if '?' in destination else '?'}sandbox_portal=1",
            "customer_id": tenant.stripe_customer_id,
            "return_url": destination,
        }

    stripe = _stripe_module()
    session = stripe.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url=destination,
    )
    portal_url = getattr(session, "url", None) or (session.get("url") if isinstance(session, dict) else None)
    log.info("billing.portal_session_created tenant_id=%s", tenant_id)
    return {
        "mode": "live",
        "portal_url": portal_url,
        "customer_id": tenant.stripe_customer_id,
        "return_url": destination,
    }


# ---------- Webhook verification ----------


def sign_webhook_payload(payload_bytes: bytes, secret: str, timestamp: int | None = None) -> str:
    """Build a Stripe-format ``t=...,v1=...`` signature header.

    Exposed so tests and the go-live dry run can produce a genuinely verifiable
    event instead of bypassing verification with a flag.
    """

    ts = int(timestamp if timestamp is not None else time.time())
    signed_payload = f"{ts}.".encode("utf-8") + payload_bytes
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def _parse_signature_header(sig_header: str) -> tuple[int | None, list[str]]:
    timestamp: int | None = None
    signatures: list[str] = []
    for part in (sig_header or "").split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                timestamp = None
        elif key == "v1":
            signatures.append(value)
    return timestamp, signatures


def _verify_sandbox_signature(payload_bytes: bytes, sig_header: str, secret: str) -> dict[str, Any]:
    """Verify an HMAC-signed sandbox payload using Stripe's signing scheme."""

    timestamp, signatures = _parse_signature_header(sig_header)
    if timestamp is None or not signatures:
        raise WebhookVerificationError("malformed_signature_header")

    age = abs(int(time.time()) - timestamp)
    if age > WEBHOOK_MAX_AGE_SECONDS:
        raise WebhookVerificationError("signature_timestamp_outside_tolerance")

    signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise WebhookVerificationError("signature_mismatch")

    try:
        event = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebhookVerificationError("payload_not_json") from exc
    if not isinstance(event, dict):
        raise WebhookVerificationError("payload_not_object")
    return event


def verify_webhook_event(payload_bytes: bytes, sig_header: str) -> dict[str, Any]:
    """Return the verified event dict, or raise ``WebhookVerificationError``.

    Fail-closed on every branch: a blank webhook secret rejects all payloads in
    both live and sandbox mode, because a deployment that cannot verify an event
    must not act on one.
    """

    settings = get_settings()
    secret = settings.stripe_webhook_secret.strip()
    if not secret:
        raise WebhookVerificationError("webhook_secret_not_configured")
    if not sig_header:
        raise WebhookVerificationError("missing_signature_header")

    if not settings.stripe_live_mode:
        return _verify_sandbox_signature(payload_bytes, sig_header, secret)

    stripe = _stripe_module()
    try:
        event = stripe.Webhook.construct_event(payload_bytes, sig_header, secret)
    except Exception as exc:  # stripe raises SignatureVerificationError / ValueError
        raise WebhookVerificationError(f"signature_verification_failed:{type(exc).__name__}") from exc
    return dict(event)


# ---------- Webhook handlers ----------


def _resolve_tenant_from_object(db: Session, obj: dict[str, Any]) -> Tenant | None:
    """Resolve the owning tenant from server-side event fields only.

    Order matters: explicit references first, then the Stripe customer ID, which
    this app itself stored on the tenant row after checkout.
    """

    candidate = (
        obj.get("client_reference_id")
        or (obj.get("metadata") or {}).get("tenant_id")
        or ((obj.get("subscription_details") or {}).get("metadata") or {}).get("tenant_id")
        or ""
    )
    candidate = str(candidate).strip()
    if candidate:
        tenant = db.get(Tenant, candidate)
        if tenant is not None:
            return tenant

    customer_id = obj.get("customer")
    if isinstance(customer_id, str) and customer_id:
        return (
            db.query(Tenant)
            .filter(Tenant.stripe_customer_id == customer_id)
            .first()
        )
    return None


def _handle_checkout_completed(db: Session, obj: dict[str, Any]) -> dict[str, Any]:
    tenant = _resolve_tenant_from_object(db, obj)
    if tenant is None:
        return {"applied": False, "reason": "tenant_not_resolved"}

    plan_tier = str((obj.get("metadata") or {}).get("plan_tier") or "").strip().lower()
    customer_id = obj.get("customer")
    subscription_id = obj.get("subscription")

    if isinstance(customer_id, str) and customer_id:
        tenant.stripe_customer_id = customer_id
    if isinstance(subscription_id, str) and subscription_id:
        tenant.stripe_subscription_id = subscription_id
    tenant.subscription_status = "active"
    tenant.cancel_at_period_end = 0
    if plan_tier in PLAN_TIERS:
        tenant.plan = plan_tier
    db.flush()
    log.info(
        "billing.checkout_completed_applied tenant_id=%s plan_tier=%s",
        tenant.id,
        tenant.plan,
    )
    return {
        "applied": True,
        "tenant_id": tenant.id,
        "plan": tenant.plan,
        "subscription_status": tenant.subscription_status,
    }


def _handle_subscription_updated(db: Session, obj: dict[str, Any]) -> dict[str, Any]:
    tenant = _resolve_tenant_from_object(db, obj)
    if tenant is None:
        return {"applied": False, "reason": "tenant_not_resolved"}

    status = str(obj.get("status") or "").strip().lower()
    if status in SUBSCRIPTION_STATUSES:
        tenant.subscription_status = status
    period_end = _from_unix(obj.get("current_period_end"))
    if period_end is not None:
        tenant.current_period_end = period_end
    tenant.cancel_at_period_end = 1 if obj.get("cancel_at_period_end") else 0
    subscription_id = obj.get("id")
    if isinstance(subscription_id, str) and subscription_id.startswith("sub_"):
        tenant.stripe_subscription_id = subscription_id
    db.flush()
    return {
        "applied": True,
        "tenant_id": tenant.id,
        "subscription_status": tenant.subscription_status,
        "cancel_at_period_end": bool(tenant.cancel_at_period_end),
        "current_period_end": tenant.current_period_end.isoformat() if tenant.current_period_end else None,
    }


def _handle_subscription_deleted(db: Session, obj: dict[str, Any]) -> dict[str, Any]:
    tenant = _resolve_tenant_from_object(db, obj)
    if tenant is None:
        return {"applied": False, "reason": "tenant_not_resolved"}

    tenant.subscription_status = "canceled"
    tenant.stripe_subscription_id = None
    tenant.cancel_at_period_end = 0
    # A cancelled subscription drops the workspace to the entry tier rather than
    # deleting it, so the tenant keeps read access to their own historical data.
    tenant.plan = "starter"
    db.flush()
    log.info("billing.subscription_canceled tenant_id=%s", tenant.id)
    return {"applied": True, "tenant_id": tenant.id, "plan": tenant.plan, "subscription_status": "canceled"}


def _handle_invoice_payment_succeeded(db: Session, obj: dict[str, Any]) -> dict[str, Any]:
    tenant = _resolve_tenant_from_object(db, obj)
    if tenant is None:
        return {"applied": False, "reason": "tenant_not_resolved"}

    invoice_id = str(obj.get("id") or "").strip()
    if not invoice_id:
        return {"applied": False, "reason": "missing_invoice_id"}

    existing = (
        db.query(TenantBillingInvoice)
        .filter(
            TenantBillingInvoice.tenant_id == tenant.id,
            TenantBillingInvoice.stripe_invoice_id == invoice_id,
        )
        .first()
    )
    if existing is not None:
        # Stripe redelivers until it gets a 2xx. Replaying must not duplicate.
        return {"applied": True, "idempotent_replay": True, "tenant_id": tenant.id, "invoice_id": invoice_id}

    invoice = TenantBillingInvoice(
        tenant_id=tenant.id,
        stripe_invoice_id=invoice_id,
        amount_paid_cents=int(obj.get("amount_paid") or 0),
        currency=str(obj.get("currency") or "gbp").lower()[:8],
        status=str(obj.get("status") or "paid").lower()[:32],
        invoice_pdf_url=obj.get("invoice_pdf") or None,
        hosted_invoice_url=obj.get("hosted_invoice_url") or None,
        paid_at=_from_unix(obj.get("status_transitions", {}).get("paid_at")) or _utcnow(),
    )
    db.add(invoice)

    # A successful payment clears a past_due state without waiting for the
    # separate subscription.updated event, which may arrive later or not at all.
    if tenant.subscription_status in ("past_due", "incomplete", "trialing"):
        tenant.subscription_status = "active"
    period_end = _from_unix((obj.get("lines", {}).get("data") or [{}])[0].get("period", {}).get("end"))
    if period_end is not None:
        tenant.current_period_end = period_end
    db.flush()
    log.info("billing.invoice_recorded tenant_id=%s invoice_id=%s", tenant.id, invoice_id)
    return {
        "applied": True,
        "idempotent_replay": False,
        "tenant_id": tenant.id,
        "invoice_id": invoice_id,
        "amount_paid_cents": invoice.amount_paid_cents,
    }


def _handle_invoice_payment_failed(db: Session, obj: dict[str, Any]) -> dict[str, Any]:
    tenant = _resolve_tenant_from_object(db, obj)
    if tenant is None:
        return {"applied": False, "reason": "tenant_not_resolved"}

    tenant.subscription_status = "past_due"
    db.flush()
    log.warning("billing.invoice_payment_failed tenant_id=%s", tenant.id)
    return {"applied": True, "tenant_id": tenant.id, "subscription_status": "past_due"}


_EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_completed,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.payment_succeeded": _handle_invoice_payment_succeeded,
    "invoice.payment_failed": _handle_invoice_payment_failed,
}


def handle_webhook_event(db: Session, payload_bytes: bytes, sig_header: str) -> dict[str, Any]:
    """Verify then apply one Stripe webhook event.

    Verification happens before any field of the payload is read, so an
    unverified payload can never reach a handler. The caller commits; this
    function only flushes, keeping the whole event application atomic.
    """

    event = verify_webhook_event(payload_bytes, sig_header)
    event_type = str(event.get("type") or "")
    obj = ((event.get("data") or {}).get("object") or {})
    if not isinstance(obj, dict):
        raise WebhookVerificationError("event_object_not_object")

    handler = _EVENT_HANDLERS.get(event_type)
    if handler is None:
        # Unknown-but-verified events are acknowledged, not errored: returning a
        # non-2xx would make Stripe retry an event this version never handles.
        return {"event_type": event_type, "handled": False, "applied": False, "reason": "event_type_not_handled"}

    result = handler(db, obj)
    return {"event_type": event_type, "handled": True, "event_id": event.get("id"), **result}


# ---------- Read model ----------


def invoice_payload(invoice: TenantBillingInvoice) -> dict[str, Any]:
    return {
        "id": invoice.id,
        "stripe_invoice_id": invoice.stripe_invoice_id,
        "amount_paid_cents": invoice.amount_paid_cents,
        "currency": invoice.currency,
        "status": invoice.status,
        "invoice_pdf_url": invoice.invoice_pdf_url,
        "hosted_invoice_url": invoice.hosted_invoice_url,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
    }


def get_billing_status(db: Session, tenant_id: str, invoice_limit: int = 24) -> dict[str, Any]:
    """Return subscription state plus the tenant's own invoice history.

    The publishable key is safe to return to a browser; the secret key never is
    and is not part of this payload.
    """

    tenant = _require_tenant(db, tenant_id)
    settings = get_settings()
    invoices = (
        db.query(TenantBillingInvoice)
        .filter(TenantBillingInvoice.tenant_id == tenant_id)
        .order_by(TenantBillingInvoice.created_at.desc(), TenantBillingInvoice.id.desc())
        .limit(invoice_limit)
        .all()
    )
    plan = (tenant.plan or "starter").lower()
    catalog = PLAN_CATALOG.get(plan)
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "plan": plan,
        "plan_name": catalog["name"] if catalog else tenant.plan,
        "plan_amount_pence": catalog["amount_pence"] if catalog else None,
        "subscription_status": tenant.subscription_status or "trialing",
        "current_period_end": tenant.current_period_end.isoformat() if tenant.current_period_end else None,
        "cancel_at_period_end": bool(tenant.cancel_at_period_end),
        "has_stripe_customer": bool(tenant.stripe_customer_id),
        "has_active_subscription": bool(tenant.stripe_subscription_id),
        "billing_mode": "live" if settings.stripe_live_mode else "sandbox",
        "publishable_key": settings.stripe_publishable_key or None,
        "currency": "gbp",
        "invoices": [invoice_payload(row) for row in invoices],
    }


def check_subscription_entitlement(tenant: Tenant) -> tuple[bool, str]:
    """Check if the tenant has active entitlement to execute live voice turns.

    Returns (is_entitled, reason).
    """
    status = (getattr(tenant, "subscription_status", "active") or "active").lower()
    period_end = getattr(tenant, "current_period_end", None)
    now = _utcnow()

    # Active or trialing tenants are entitled
    if status in ("active", "trialing"):
        return True, status

    # Past due or canceled with unexpired grace period
    if status in ("past_due", "canceled"):
        if period_end:
            p_end_utc = period_end if period_end.tzinfo else period_end.replace(tzinfo=timezone.utc)
            if p_end_utc >= now:
                return True, f"grace_period_active_until_{p_end_utc.isoformat()}"
        return False, f"subscription_{status}"

    return False, f"subscription_{status}"

