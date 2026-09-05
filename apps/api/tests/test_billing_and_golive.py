"""Day 53: Stripe billing lifecycle, RBAC gating, isolation, and go-live dry run.

Verification-first structure. The webhook tests deliberately drive the *real*
verification path (an HMAC-signed body in sandbox mode) rather than patching the
verifier out, because "unverified payloads are rejected" is the security property
under test — asserting it against a stubbed verifier would prove nothing.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import voxflow_api.auth as auth_mod
from voxflow_api.auth import AuthUser, normalized_email_hash
from voxflow_api.config import get_settings
from voxflow_api.db import (
    Tenant,
    TenantBillingInvoice,
    TenantMember,
    reset_db,
    session_scope,
)
from voxflow_api.main import create_app
from voxflow_api.services import billing_service


REPO_ROOT = Path(__file__).resolve().parents[3]

TENANT_A = "billing-alpha"
TENANT_B = "billing-beta"

WEBHOOK_SECRET = "whsec_test_day53_shared_secret"

IDENTITIES = {
    "a-owner-token": AuthUser(user_id="usr-a-owner", email="owner@alpha.test"),
    "a-operator-token": AuthUser(user_id="usr-a-operator", email="operator@alpha.test"),
    "a-viewer-token": AuthUser(user_id="usr-a-viewer", email="viewer@alpha.test"),
    "b-owner-token": AuthUser(user_id="usr-b-owner", email="owner@beta.test"),
}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _membership(tenant_id: str, user_id: str, email: str, role: str) -> TenantMember:
    return TenantMember(
        id=f"{tenant_id}-{user_id}",
        tenant_id=tenant_id,
        user_id=user_id,
        subject_email_hash=normalized_email_hash(email, fallback_subject=user_id),
        role=role,
        status="active",
        invited_by="billing-test",
        activated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def billing_client(monkeypatch):
    """Two tenants, four identities, sandbox Stripe with a real webhook secret."""

    monkeypatch.setenv("TENANT_AUTHORIZATION_ENFORCED", "true")
    monkeypatch.setenv("DEMO_MODE_ENABLED", "false")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")  # sandbox mode, no network
    monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", "pk_test_day53")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    get_settings.cache_clear()
    monkeypatch.setattr(auth_mod, "_verify_token", lambda token: IDENTITIES.get(token))

    reset_db()
    with session_scope() as db:
        db.add_all(
            [
                Tenant(id=TENANT_A, name="Alpha Logistics", plan="starter"),
                Tenant(id=TENANT_B, name="Beta Freight", plan="starter"),
                _membership(TENANT_A, "usr-a-owner", "owner@alpha.test", "owner"),
                _membership(TENANT_A, "usr-a-operator", "operator@alpha.test", "operator"),
                _membership(TENANT_A, "usr-a-viewer", "viewer@alpha.test", "viewer"),
                _membership(TENANT_B, "usr-b-owner", "owner@beta.test", "owner"),
            ]
        )

    with TestClient(create_app()) as client:
        yield client

    get_settings.cache_clear()


def _post_event(client: TestClient, event: dict, *, secret: str = WEBHOOK_SECRET, timestamp=None):
    """Send a genuinely signed webhook through the public endpoint."""

    body = json.dumps(event).encode("utf-8")
    sig = billing_service.sign_webhook_payload(body, secret, timestamp=timestamp)
    return client.post(
        "/api/billing/webhook",
        content=body,
        headers={"stripe-signature": sig, "content-type": "application/json"},
    )


def _checkout_completed_event(tenant_id: str, plan_tier: str = "growth") -> dict:
    return {
        "id": f"evt_checkout_{tenant_id}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_test_{tenant_id}",
                "client_reference_id": tenant_id,
                "customer": f"cus_test_{tenant_id}",
                "subscription": f"sub_test_{tenant_id}",
                "metadata": {"tenant_id": tenant_id, "plan_tier": plan_tier},
            }
        },
    }


# ---------- Checkout session ----------


def test_owner_creates_checkout_session_in_sandbox_mode(billing_client):
    r = billing_client.post(
        f"/api/tenants/{TENANT_A}/billing/checkout",
        json={
            "plan_tier": "growth",
            "success_url": "http://localhost:3000/dashboard/settings?billing=success",
            "cancel_url": "http://localhost:3000/pricing",
        },
        headers=_headers("a-owner-token"),
    )
    assert r.status_code == 200, r.text
    checkout = r.json()["checkout"]
    assert checkout["mode"] == "sandbox"
    assert checkout["plan_tier"] == "growth"
    assert checkout["client_reference_id"] == TENANT_A
    assert checkout["metadata"] == {"tenant_id": TENANT_A, "plan_tier": "growth"}
    assert checkout["amount_pence"] == 44900
    assert checkout["currency"] == "gbp"
    assert checkout["checkout_url"].startswith("http://localhost:3000/")


def test_checkout_rejects_unknown_plan_tier(billing_client):
    r = billing_client.post(
        f"/api/tenants/{TENANT_A}/billing/checkout",
        json={
            "plan_tier": "platinum",
            "success_url": "http://localhost:3000/ok",
            "cancel_url": "http://localhost:3000/no",
        },
        headers=_headers("a-owner-token"),
    )
    assert r.status_code == 422


def test_checkout_rejects_non_http_redirect_url(billing_client):
    """A crafted redirect must not become an open redirect off an http(s) origin."""

    r = billing_client.post(
        f"/api/tenants/{TENANT_A}/billing/checkout",
        json={
            "plan_tier": "starter",
            "success_url": "javascript:alert(1)",
            "cancel_url": "http://localhost:3000/pricing",
        },
        headers=_headers("a-owner-token"),
    )
    assert r.status_code == 422


def test_checkout_on_unknown_tenant_is_404(billing_client):
    r = billing_client.post(
        "/api/tenants/does-not-exist/billing/checkout",
        json={
            "plan_tier": "starter",
            "success_url": "http://localhost:3000/ok",
            "cancel_url": "http://localhost:3000/no",
        },
        headers=_headers("a-owner-token"),
    )
    assert r.status_code == 404


# ---------- Customer portal ----------


def test_portal_requires_existing_stripe_customer(billing_client):
    r = billing_client.post(
        f"/api/tenants/{TENANT_A}/billing/portal",
        json={"return_url": "http://localhost:3000/dashboard/settings"},
        headers=_headers("a-owner-token"),
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "no_stripe_customer_for_tenant"


def test_portal_session_after_checkout_completes(billing_client):
    assert _post_event(billing_client, _checkout_completed_event(TENANT_A)).status_code == 200

    r = billing_client.post(
        f"/api/tenants/{TENANT_A}/billing/portal",
        json={"return_url": "http://localhost:3000/dashboard/settings"},
        headers=_headers("a-owner-token"),
    )
    assert r.status_code == 200, r.text
    portal = r.json()["portal"]
    assert portal["mode"] == "sandbox"
    assert portal["customer_id"] == f"cus_test_{TENANT_A}"
    assert portal["portal_url"].startswith("http://localhost:3000/dashboard/settings")


# ---------- Webhook signature verification (fail-closed) ----------


def test_webhook_rejects_missing_signature_header(billing_client):
    r = billing_client.post(
        "/api/billing/webhook",
        content=json.dumps(_checkout_completed_event(TENANT_A)).encode(),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400
    assert "missing_signature_header" in r.json()["detail"]


def test_webhook_rejects_wrong_secret(billing_client):
    r = _post_event(billing_client, _checkout_completed_event(TENANT_A), secret="whsec_attacker_guess")
    assert r.status_code == 400
    assert "signature_mismatch" in r.json()["detail"]


def test_webhook_rejects_tampered_body_under_valid_signature(billing_client):
    """Signature covers the exact bytes; changing one field must invalidate it."""

    event = _checkout_completed_event(TENANT_A)
    body = json.dumps(event).encode("utf-8")
    sig = billing_service.sign_webhook_payload(body, WEBHOOK_SECRET)

    event["data"]["object"]["client_reference_id"] = TENANT_B
    tampered = json.dumps(event).encode("utf-8")

    r = billing_client.post(
        "/api/billing/webhook",
        content=tampered,
        headers={"stripe-signature": sig, "content-type": "application/json"},
    )
    assert r.status_code == 400
    assert "signature_mismatch" in r.json()["detail"]
    with session_scope() as db:
        assert db.get(Tenant, TENANT_B).plan == "starter"


def test_webhook_rejects_replay_outside_timestamp_tolerance(billing_client):
    stale = int(time.time()) - (billing_service.WEBHOOK_MAX_AGE_SECONDS + 60)
    r = _post_event(billing_client, _checkout_completed_event(TENANT_A), timestamp=stale)
    assert r.status_code == 400
    assert "outside_tolerance" in r.json()["detail"]


def test_webhook_fails_closed_when_secret_is_unconfigured(billing_client, monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    try:
        r = _post_event(billing_client, _checkout_completed_event(TENANT_A))
        assert r.status_code == 400
        assert "webhook_secret_not_configured" in r.json()["detail"]
    finally:
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
        get_settings.cache_clear()


def test_verified_but_unhandled_event_is_acknowledged_not_errored(billing_client):
    """Returning non-2xx would make Stripe retry an event forever."""

    r = _post_event(
        billing_client,
        {"id": "evt_x", "type": "customer.source.expiring", "data": {"object": {}}},
    )
    assert r.status_code == 200
    assert r.json()["handled"] is False


# ---------- Webhook event handling ----------


def test_checkout_completed_activates_subscription_and_plan(billing_client):
    r = _post_event(billing_client, _checkout_completed_event(TENANT_A, "growth"))
    assert r.status_code == 200, r.text
    assert r.json()["applied"] is True

    with session_scope() as db:
        tenant = db.get(Tenant, TENANT_A)
        assert tenant.stripe_customer_id == f"cus_test_{TENANT_A}"
        assert tenant.stripe_subscription_id == f"sub_test_{TENANT_A}"
        assert tenant.subscription_status == "active"
        assert tenant.plan == "growth"


def test_subscription_updated_records_period_end_and_cancel_flag(billing_client):
    _post_event(billing_client, _checkout_completed_event(TENANT_A))
    period_end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())

    r = _post_event(
        billing_client,
        {
            "id": "evt_sub_updated",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": f"sub_test_{TENANT_A}",
                    "customer": f"cus_test_{TENANT_A}",
                    "status": "past_due",
                    "current_period_end": period_end,
                    "cancel_at_period_end": True,
                    "metadata": {"tenant_id": TENANT_A},
                }
            },
        },
    )
    assert r.status_code == 200, r.text

    with session_scope() as db:
        tenant = db.get(Tenant, TENANT_A)
        assert tenant.subscription_status == "past_due"
        assert tenant.cancel_at_period_end == 1
        assert tenant.current_period_end is not None


def test_subscription_deleted_cancels_and_drops_to_starter(billing_client):
    _post_event(billing_client, _checkout_completed_event(TENANT_A, "enterprise"))
    with session_scope() as db:
        assert db.get(Tenant, TENANT_A).plan == "enterprise"

    r = _post_event(
        billing_client,
        {
            "id": "evt_sub_deleted",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": f"sub_test_{TENANT_A}",
                    "customer": f"cus_test_{TENANT_A}",
                    "status": "canceled",
                    "metadata": {"tenant_id": TENANT_A},
                }
            },
        },
    )
    assert r.status_code == 200, r.text

    with session_scope() as db:
        tenant = db.get(Tenant, TENANT_A)
        assert tenant.subscription_status == "canceled"
        assert tenant.plan == "starter"
        assert tenant.stripe_subscription_id is None


def _invoice_event(tenant_id: str, invoice_id: str = "in_test_001") -> dict:
    return {
        "id": f"evt_invoice_{invoice_id}",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": invoice_id,
                "customer": f"cus_test_{tenant_id}",
                "amount_paid": 14900,
                "currency": "gbp",
                "status": "paid",
                "invoice_pdf": "https://stripe.test/invoice.pdf",
                "hosted_invoice_url": "https://stripe.test/invoice",
                "status_transitions": {"paid_at": int(time.time())},
                "metadata": {"tenant_id": tenant_id},
            }
        },
    }


def test_invoice_payment_succeeded_records_invoice_with_pdf_url(billing_client):
    _post_event(billing_client, _checkout_completed_event(TENANT_A))
    r = _post_event(billing_client, _invoice_event(TENANT_A))
    assert r.status_code == 200, r.text
    assert r.json()["idempotent_replay"] is False

    with session_scope() as db:
        rows = db.query(TenantBillingInvoice).filter(TenantBillingInvoice.tenant_id == TENANT_A).all()
        assert len(rows) == 1
        assert rows[0].amount_paid_cents == 14900
        assert rows[0].currency == "gbp"
        assert rows[0].status == "paid"
        assert rows[0].invoice_pdf_url == "https://stripe.test/invoice.pdf"


def test_invoice_replay_is_idempotent(billing_client):
    """Stripe redelivers until 2xx — replaying must not double-bill the ledger."""

    _post_event(billing_client, _checkout_completed_event(TENANT_A))
    first = _post_event(billing_client, _invoice_event(TENANT_A))
    second = _post_event(billing_client, _invoice_event(TENANT_A))
    third = _post_event(billing_client, _invoice_event(TENANT_A))

    assert first.json()["idempotent_replay"] is False
    assert second.json()["idempotent_replay"] is True
    assert third.json()["idempotent_replay"] is True

    with session_scope() as db:
        count = db.query(TenantBillingInvoice).filter(TenantBillingInvoice.tenant_id == TENANT_A).count()
        assert count == 1


def test_checkout_completed_replay_is_idempotent(billing_client):
    for _ in range(3):
        assert _post_event(billing_client, _checkout_completed_event(TENANT_A, "growth")).status_code == 200

    with session_scope() as db:
        tenant = db.get(Tenant, TENANT_A)
        assert tenant.plan == "growth"
        assert tenant.subscription_status == "active"


def test_invoice_payment_failed_marks_past_due(billing_client):
    _post_event(billing_client, _checkout_completed_event(TENANT_A))
    r = _post_event(
        billing_client,
        {
            "id": "evt_invoice_failed",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": "in_failed_001",
                    "customer": f"cus_test_{TENANT_A}",
                    "metadata": {"tenant_id": TENANT_A},
                }
            },
        },
    )
    assert r.status_code == 200, r.text
    with session_scope() as db:
        assert db.get(Tenant, TENANT_A).subscription_status == "past_due"


def test_webhook_for_unknown_tenant_changes_nothing(billing_client):
    r = _post_event(billing_client, _checkout_completed_event("ghost-tenant"))
    assert r.status_code == 200
    assert r.json()["applied"] is False
    assert r.json()["reason"] == "tenant_not_resolved"


# ---------- 3-tier RBAC gating ----------


@pytest.mark.parametrize("token", ["a-operator-token", "a-viewer-token"])
def test_non_owner_cannot_start_checkout(billing_client, token):
    r = billing_client.post(
        f"/api/tenants/{TENANT_A}/billing/checkout",
        json={
            "plan_tier": "growth",
            "success_url": "http://localhost:3000/ok",
            "cancel_url": "http://localhost:3000/no",
        },
        headers=_headers(token),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "tenant_role_insufficient"


@pytest.mark.parametrize("token", ["a-operator-token", "a-viewer-token"])
def test_non_owner_cannot_open_customer_portal(billing_client, token):
    r = billing_client.post(
        f"/api/tenants/{TENANT_A}/billing/portal",
        json={},
        headers=_headers(token),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "tenant_role_insufficient"


@pytest.mark.parametrize("token", ["a-owner-token", "a-operator-token", "a-viewer-token"])
def test_all_three_roles_can_read_billing_status(billing_client, token):
    r = billing_client.get(f"/api/tenants/{TENANT_A}/billing/status", headers=_headers(token))
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["tenant_id"] == TENANT_A
    assert payload["subscription_status"] == "trialing"
    assert payload["billing_mode"] == "sandbox"
    assert payload["publishable_key"] == "pk_test_day53"
    assert set(payload["catalog"]) == {"starter", "growth", "enterprise"}


def test_billing_status_never_returns_a_secret_key(billing_client):
    r = billing_client.get(f"/api/tenants/{TENANT_A}/billing/status", headers=_headers("a-owner-token"))
    body = r.text.lower()
    assert "sk_" not in body
    assert "secret_key" not in body
    assert "whsec" not in body


def test_anonymous_request_is_rejected(billing_client):
    assert billing_client.get(f"/api/tenants/{TENANT_A}/billing/status").status_code == 401


# ---------- Multi-tenant isolation ----------


def test_tenant_b_owner_cannot_read_tenant_a_billing(billing_client):
    r = billing_client.get(f"/api/tenants/{TENANT_A}/billing/status", headers=_headers("b-owner-token"))
    assert r.status_code == 403
    assert r.json()["detail"] == "tenant_membership_required"


def test_tenant_b_owner_cannot_start_checkout_for_tenant_a(billing_client):
    r = billing_client.post(
        f"/api/tenants/{TENANT_A}/billing/checkout",
        json={
            "plan_tier": "enterprise",
            "success_url": "http://localhost:3000/ok",
            "cancel_url": "http://localhost:3000/no",
        },
        headers=_headers("b-owner-token"),
    )
    assert r.status_code == 403
    with session_scope() as db:
        assert db.get(Tenant, TENANT_A).plan == "starter"


def test_tenant_b_owner_cannot_open_tenant_a_portal(billing_client):
    _post_event(billing_client, _checkout_completed_event(TENANT_A))
    r = billing_client.post(
        f"/api/tenants/{TENANT_A}/billing/portal",
        json={},
        headers=_headers("b-owner-token"),
    )
    assert r.status_code == 403


def test_invoice_ledger_is_strictly_tenant_scoped(billing_client):
    _post_event(billing_client, _checkout_completed_event(TENANT_A))
    _post_event(billing_client, _checkout_completed_event(TENANT_B))
    _post_event(billing_client, _invoice_event(TENANT_A, "in_alpha_001"))
    _post_event(billing_client, _invoice_event(TENANT_B, "in_beta_001"))

    a = billing_client.get(f"/api/tenants/{TENANT_A}/billing/status", headers=_headers("a-owner-token")).json()
    b = billing_client.get(f"/api/tenants/{TENANT_B}/billing/status", headers=_headers("b-owner-token")).json()

    assert [i["stripe_invoice_id"] for i in a["invoices"]] == ["in_alpha_001"]
    assert [i["stripe_invoice_id"] for i in b["invoices"]] == ["in_beta_001"]


def test_same_invoice_id_across_tenants_is_allowed(billing_client):
    """Uniqueness is (tenant_id, stripe_invoice_id), not the invoice ID alone."""

    _post_event(billing_client, _checkout_completed_event(TENANT_A))
    _post_event(billing_client, _checkout_completed_event(TENANT_B))
    assert _post_event(billing_client, _invoice_event(TENANT_A, "in_shared")).json()["applied"] is True
    assert _post_event(billing_client, _invoice_event(TENANT_B, "in_shared")).json()["applied"] is True

    with session_scope() as db:
        assert db.query(TenantBillingInvoice).count() == 2


# ---------- Public config endpoint ----------


def test_public_billing_config_exposes_no_secret(billing_client):
    r = billing_client.get("/api/billing/config")
    assert r.status_code == 200
    payload = r.json()
    assert payload["billing_mode"] == "sandbox"
    assert payload["publishable_key"] == "pk_test_day53"
    assert payload["currency"] == "gbp"
    assert payload["catalog"]["starter"]["amount_pence"] == 14900
    assert payload["catalog"]["growth"]["amount_pence"] == 44900
    assert payload["catalog"]["enterprise"]["amount_pence"] == 149900
    assert "sk_" not in r.text
    assert "whsec" not in r.text


# ---------- Schema & migration presence ----------


def test_migration_022_declares_every_billing_column():
    sql = (REPO_ROOT / "migrations" / "022_stripe_billing.sql").read_text()
    for column in (
        "stripe_customer_id",
        "stripe_subscription_id",
        "subscription_status",
        "current_period_end",
        "cancel_at_period_end",
    ):
        assert column in sql, f"{column} missing from migration 022"
    assert "CREATE TABLE IF NOT EXISTS tenant_billing_invoices" in sql
    assert "uq_tenant_billing_invoice_stripe_id" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_sqlite_billing_shim_is_idempotent():
    """Repeated startup on an existing local database must not raise."""

    from voxflow_api.db import _ensure_tenant_billing_columns_sqlite

    _ensure_tenant_billing_columns_sqlite()
    _ensure_tenant_billing_columns_sqlite()


# ---------- Go-live dry run script ----------


def _run_dry_run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "golive_dry_run.py"), *args],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO_ROOT),
    )


def test_golive_dry_run_script_exists_and_is_executable():
    script = REPO_ROOT / "scripts" / "golive_dry_run.py"
    assert script.exists()
    assert script.read_text().startswith("#!/usr/bin/env python3")


def test_golive_dry_run_json_reports_all_seven_pillars():
    result = _run_dry_run("--json", "--skip-slow")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["total_checks"] == 7
    names = [check["name"] for check in payload["checks"]]
    assert names == [
        "database_migrations",
        "multi_tenant_isolation",
        "telephony_and_simulator",
        "stripe_billing_webhook",
        "voice_eval_threshold",
        "gdpr_retention_lifecycle",
        "web_production_build",
    ]
    for check in payload["checks"]:
        assert check["status"] in {"pass", "fail", "skip", "warn"}


def test_golive_dry_run_stripe_pillar_verifies_a_real_signature():
    result = _run_dry_run("--json", "--skip-slow")
    payload = json.loads(result.stdout)
    stripe_check = next(c for c in payload["checks"] if c["name"] == "stripe_billing_webhook")
    assert stripe_check["status"] == "pass", stripe_check
    assert stripe_check["evidence"]["signed_event_accepted"] is True
    assert stripe_check["evidence"]["tampered_event_rejected"] is True
    assert stripe_check["evidence"]["unsigned_event_rejected"] is True


def test_golive_dry_run_human_output_has_status_symbols():
    result = _run_dry_run("--skip-slow")
    assert result.returncode == 0, result.stderr
    assert "VoxFlow Go-Live Preflight" in result.stdout
    assert ("PASS" in result.stdout) or ("✅" in result.stdout)


def test_golive_dry_run_strict_flag_exits_nonzero_on_failure():
    """--strict must be a real gate, not decoration."""

    result = _run_dry_run("--json", "--strict", "--skip-slow", "--force-fail", "database_migrations")
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ready"] is False
    failed = next(c for c in payload["checks"] if c["name"] == "database_migrations")
    assert failed["status"] == "fail"


def test_golive_dry_run_non_strict_exits_zero_even_with_failure():
    result = _run_dry_run("--json", "--skip-slow", "--force-fail", "database_migrations")
    assert result.returncode == 0
    assert json.loads(result.stdout)["ready"] is False
