"""Comprehensive Phase 2 Revenue Infrastructure Tests.

Verifies:
1. Exact founder-approved tier pricing (£149 / £449 / £1,499).
2. Population of `subscriptions` and `invoices` tables from Stripe webhook events.
3. Dunning: `past_due` (grace period) on failed payment with scheduled retry.
4. Auto-suspension: `suspended` when Stripe payment retries are exhausted.
5. Visibility in `/superadmin` of tenant subscription & suspension states.
6. Idempotency: replaying webhook events never double-charges or duplicates records.
7. Fail-closed signature verification on invalid or tampered payloads.
8. Successful payment clearing dunning/suspension back to `active`.
"""

from __future__ import annotations

import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from voxflow_api.config import get_settings
from voxflow_api.db import Invoice, Subscription, Tenant, TenantBillingInvoice, TenantMember, session_scope
from voxflow_api.main import create_app
from voxflow_api.services.billing_service import (
    PLAN_CATALOG,
    SUBSCRIPTION_STATUSES,
    WebhookVerificationError,
    handle_webhook_event,
    sign_webhook_payload,
)


@pytest.fixture(autouse=True)
def _reset_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


@pytest.fixture
def secret(monkeypatch) -> str:
    s = "whsec_test_phase2_revenue_fixture"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", s)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    get_settings.cache_clear()
    return s


@pytest.fixture
def sample_tenant() -> str:
    tenant_id = f"test-p2-{int(time.time() * 1000)}"
    with session_scope() as db:
        t = Tenant(
            id=tenant_id,
            name=f"Phase 2 Test Tenant {tenant_id}",
            plan="starter",
            subscription_status="trialing",
            failed_payment_count=0,
        )
        db.add(t)
    return tenant_id


def _sign(payload: dict[str, Any], secret: str, timestamp: int | None = None) -> tuple[bytes, str]:
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = sign_webhook_payload(payload_bytes, secret, timestamp=timestamp)
    return payload_bytes, sig


def test_01_founder_approved_pricing_tiers():
    """Definition of Done 1: All three tiers match confirmed UK B2B pricing."""
    assert PLAN_CATALOG["starter"]["amount_pence"] == 14900  # £149
    assert PLAN_CATALOG["growth"]["amount_pence"] == 44900   # £449
    assert PLAN_CATALOG["enterprise"]["amount_pence"] == 149900  # £1,499
    assert "suspended" in SUBSCRIPTION_STATUSES


def test_02_checkout_session_completed_populates_subscriptions_table(sample_tenant, secret, monkeypatch):
    """Definition of Done 2a: checkout.session.completed populates subscriptions table."""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")  # Deterministic sandbox

    sub_id = f"sub_{sample_tenant}"
    payload = {
        "id": f"evt_checkout_{sample_tenant}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_{sample_tenant}",
                "client_reference_id": sample_tenant,
                "customer": f"cus_{sample_tenant}",
                "subscription": sub_id,
                "metadata": {"plan_tier": "growth", "tenant_id": sample_tenant},
            }
        },
    }

    raw, sig = _sign(payload, secret)

    with session_scope() as db:
        res = handle_webhook_event(db, raw, sig)
        assert res["applied"] is True
        assert res["subscription_status"] == "active"
        assert res["plan"] == "growth"

        # Verify Tenant row
        tenant = db.get(Tenant, sample_tenant)
        assert tenant.subscription_status == "active"
        assert tenant.plan == "growth"
        assert tenant.stripe_subscription_id == sub_id
        assert tenant.stripe_customer_id == f"cus_{sample_tenant}"
        assert tenant.failed_payment_count == 0

        # Verify dedicated Subscriptions table
        sub = db.get(Subscription, sub_id)
        assert sub is not None
        assert sub.tenant_id == sample_tenant
        assert sub.status == "active"
        assert sub.plan_tier == "growth"
        assert sub.failed_payment_count == 0


def test_03_invoice_payment_succeeded_populates_invoices_and_is_idempotent(sample_tenant, secret, monkeypatch):
    """Definition of Done 2b & 4: invoice.payment_succeeded records invoices table and replays idempotently."""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")

    invoice_id = f"in_test_{sample_tenant}"
    payload = {
        "id": f"evt_inv_paid_{sample_tenant}",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": invoice_id,
                "customer": f"cus_{sample_tenant}",
                "client_reference_id": sample_tenant,
                "subscription": f"sub_{sample_tenant}",
                "amount_paid": 44900,
                "amount_due": 44900,
                "currency": "gbp",
                "status": "paid",
                "hosted_invoice_url": "https://invoice.stripe.com/test",
                "status_transitions": {"paid_at": int(time.time())},
            }
        },
    }

    raw, sig = _sign(payload, secret)

    # First delivery
    with session_scope() as db:
        res1 = handle_webhook_event(db, raw, sig)
        assert res1["applied"] is True
        assert res1["idempotent_replay"] is False
        assert res1["invoice_id"] == invoice_id

        # Verify Invoice table
        inv = db.get(Invoice, invoice_id)
        assert inv is not None
        assert inv.tenant_id == sample_tenant
        assert inv.status == "paid"
        assert inv.amount_paid_pence == 44900

        # Verify TenantBillingInvoice legacy parity
        t_inv = db.query(TenantBillingInvoice).filter_by(stripe_invoice_id=invoice_id).first()
        assert t_inv is not None

    # Idempotent replay: exact duplicate event delivery
    with session_scope() as db:
        res2 = handle_webhook_event(db, raw, sig)
        assert res2["applied"] is True
        assert res2["idempotent_replay"] is True

        # Count must remain 1
        count = db.query(Invoice).filter_by(id=invoice_id).count()
        assert count == 1


def test_04_dunning_grace_period_when_retry_is_scheduled(sample_tenant, secret, monkeypatch):
    """Definition of Done 3a: invoice.payment_failed with next_payment_attempt sets grace period (past_due)."""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")

    invoice_id = f"in_fail_retry_{sample_tenant}"
    payload = {
        "id": f"evt_fail_1_{sample_tenant}",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": invoice_id,
                "client_reference_id": sample_tenant,
                "subscription": f"sub_{sample_tenant}",
                "amount_due": 14900,
                "currency": "gbp",
                "attempt_count": 1,
                "next_payment_attempt": int(time.time()) + 86400,  # retry tomorrow
            }
        },
    }

    raw, sig = _sign(payload, secret)

    with session_scope() as db:
        res = handle_webhook_event(db, raw, sig)
        assert res["applied"] is True
        assert res["subscription_status"] == "past_due"
        assert res["action"] == "grace_period"
        assert res["failed_payment_count"] == 1

        tenant = db.get(Tenant, sample_tenant)
        assert tenant.subscription_status == "past_due"
        assert tenant.failed_payment_count == 1

        inv = db.get(Invoice, invoice_id)
        assert inv is not None
        assert inv.status == "failed"


def test_05_dunning_auto_suspension_when_retries_exhausted(sample_tenant, secret, monkeypatch):
    """Definition of Done 3b: invoice.payment_failed with next_payment_attempt=None auto-suspends tenant."""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")

    invoice_id = f"in_fail_exhausted_{sample_tenant}"
    payload = {
        "id": f"evt_fail_final_{sample_tenant}",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": invoice_id,
                "client_reference_id": sample_tenant,
                "subscription": f"sub_{sample_tenant}",
                "amount_due": 14900,
                "currency": "gbp",
                "attempt_count": 4,
                "next_payment_attempt": None,  # Retries exhausted!
            }
        },
    }

    raw, sig = _sign(payload, secret)

    with session_scope() as db:
        res = handle_webhook_event(db, raw, sig)
        assert res["applied"] is True
        assert res["subscription_status"] == "suspended"
        assert res["action"] == "suspended"

        tenant = db.get(Tenant, sample_tenant)
        assert tenant.subscription_status == "suspended"

        # Check Subscription table reflects suspension
        sub = db.get(Subscription, f"sub_{sample_tenant}")
        if sub:
            assert sub.status == "suspended"


def test_06_superadmin_telemetry_shows_suspension_and_dunning_states(sample_tenant, client, monkeypatch):
    """Definition of Done 3c: Superadmin endpoint /api/superadmin/tenants exposes suspension state."""
    # Ensure tenant is suspended
    with session_scope() as db:
        t = db.get(Tenant, sample_tenant)
        t.subscription_status = "suspended"
        t.failed_payment_count = 4
        db.flush()

    # Configure platform admin
    monkeypatch.setenv("PLATFORM_ADMIN_USER_IDS", "superadmin-phase2-tester")

    headers = {
        "Authorization": "Bearer fake-token",
        "X-Supabase-User-Id": "superadmin-phase2-tester",
    }
    r = client.get("/api/superadmin/tenants", headers=headers)
    assert r.status_code == 200, f"Superadmin returned {r.status_code}: {r.text}"
    body = r.json()
    assert "tenants" in body

    match = next((row for row in body["tenants"] if row["tenant_id"] == sample_tenant), None)
    assert match is not None, f"Tenant {sample_tenant} not found in superadmin response"
    assert match["subscription_status"] == "suspended"
    assert match["failed_payment_count"] == 4


def test_07_webhook_signature_verification_rejects_tampered_payload(sample_tenant, secret, monkeypatch):
    """Definition of Done 4: Webhook verification rejects forged or tampered signatures."""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")

    payload = {"id": "evt_tampered", "type": "checkout.session.completed", "data": {}}
    raw, _ = _sign(payload, secret)
    bad_sig = "t=1700000000,v1=0000000000000000000000000000000000000000000000000000000000000000"

    with session_scope() as db:
        with pytest.raises(WebhookVerificationError):
            handle_webhook_event(db, raw, bad_sig)


def test_08_subsequent_successful_payment_restores_suspended_tenant_to_active(sample_tenant, secret, monkeypatch):
    """Verify state recovery: settlement clears suspension back to active."""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")

    # Put in suspended state
    with session_scope() as db:
        t = db.get(Tenant, sample_tenant)
        t.subscription_status = "suspended"
        t.failed_payment_count = 3
        db.flush()

    invoice_id = f"in_settle_{sample_tenant}"
    payload = {
        "id": f"evt_settle_{sample_tenant}",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": invoice_id,
                "client_reference_id": sample_tenant,
                "subscription": f"sub_{sample_tenant}",
                "amount_paid": 14900,
                "currency": "gbp",
                "status": "paid",
            }
        },
    }

    raw, sig = _sign(payload, secret)
    with session_scope() as db:
        res = handle_webhook_event(db, raw, sig)
        assert res["applied"] is True

        tenant = db.get(Tenant, sample_tenant)
        assert tenant.subscription_status == "active"
        assert tenant.failed_payment_count == 0
