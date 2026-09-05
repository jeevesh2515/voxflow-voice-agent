"""Checkout wiring: licensed (quantity) + metered (no quantity) line items.

Proves the metered price ids configured in the same settings source as the
subscription price surface in the Stripe Checkout Session line_items, and that
the missing-config paths degrade instead of 500ing.
"""

from __future__ import annotations

import pytest

from voxflow_api.config import get_settings
from voxflow_api.db import SessionLocal, Tenant, reset_db, session_scope
from voxflow_api.services import billing_service

TENANT_A = "ck-alpha"
CUSTOMER_A = "cus_ck_alpha"
LIC_STARTER = "price_lic_starter"
MET_STARTER = "price_met_starter"
LIC_ENTERPRISE = "price_lic_enterprise"
MET_ENTERPRISE = "price_met_enterprise"


class FakeSessions:
    def __init__(self, fake: "FakeStripe") -> None:
        self._fake = fake

    def create(self, **kwargs):
        self._fake.checkout_calls.append(kwargs)
        return type("Session", (), {"id": "cs_live_1", "url": "https://checkout.stripe.com/c/pay/cs_live_1"})()


class FakeStripe:
    """Recording double: checkout.Session.create for checkout wiring tests."""

    def __init__(self) -> None:
        self.checkout_calls: list[dict] = []
        self.checkout = type("Checkout", (), {"Session": FakeSessions(self)})()


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_mock_dummy_key")
    monkeypatch.setenv("STRIPE_METER_EVENT_NAME", "voxflow_voice_minutes")
    monkeypatch.setenv("STRIPE_PRICE_STARTER", LIC_STARTER)
    monkeypatch.setenv("STRIPE_METER_PRICE_STARTER", MET_STARTER)
    monkeypatch.setenv("STRIPE_PRICE_ENTERPRISE", LIC_ENTERPRISE)
    monkeypatch.setenv("STRIPE_METER_PRICE_ENTERPRISE", MET_ENTERPRISE)
    get_settings.cache_clear()
    reset_db()
    with session_scope() as db:
        db.add(Tenant(id=TENANT_A, name="Checkout Alpha", plan="starter",
                      active=1, stripe_customer_id=CUSTOMER_A))


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def fake_stripe(monkeypatch):
    fake = FakeStripe()
    monkeypatch.setattr(billing_service, "_stripe_module", lambda: fake)
    return fake


def test_checkout_live_includes_licensed_and_metered_line_items(fresh_db, fake_stripe, db):
    result = billing_service.create_checkout_session(
        db, TENANT_A, "starter", "https://app.voxflow.ai/success", "https://app.voxflow.ai/cancel")

    assert result["mode"] == "live"
    assert result["meter_price_id"] == MET_STARTER
    assert len(fake_stripe.checkout_calls) == 1
    params = fake_stripe.checkout_calls[0]
    assert params["mode"] == "subscription"
    # Licensed price carries quantity; metered price must NOT.
    assert params["line_items"] == [
        {"price": LIC_STARTER, "quantity": 1},
        {"price": MET_STARTER},
    ]
    assert params["metadata"] == {"tenant_id": TENANT_A, "plan_tier": "starter"}
    assert params["customer"] == CUSTOMER_A


def test_checkout_metered_missing_falls_back_to_licensed_only(fresh_db, fake_stripe, db, monkeypatch):
    monkeypatch.setenv("STRIPE_METER_PRICE_STARTER", "")
    get_settings.cache_clear()

    result = billing_service.create_checkout_session(
        db, TENANT_A, "starter", "https://app.voxflow.ai/success", "https://app.voxflow.ai/cancel")

    assert result["meter_price_id"] is None
    assert fake_stripe.checkout_calls[0]["line_items"] == [{"price": LIC_STARTER, "quantity": 1}]


def test_checkout_licensed_missing_sends_only_metered_without_quantity(fresh_db, fake_stripe, db, monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "")
    get_settings.cache_clear()

    result = billing_service.create_checkout_session(
        db, TENANT_A, "starter", "https://app.voxflow.ai/success", "https://app.voxflow.ai/cancel")

    assert result["mode"] == "live"
    assert fake_stripe.checkout_calls[0]["line_items"] == [{"price": MET_STARTER}]


def test_checkout_both_missing_uses_inline_price_data(fresh_db, fake_stripe, db, monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "")
    monkeypatch.setenv("STRIPE_METER_PRICE_STARTER", "")
    get_settings.cache_clear()

    result = billing_service.create_checkout_session(
        db, TENANT_A, "starter", "https://app.voxflow.ai/success", "https://app.voxflow.ai/cancel")

    assert result["mode"] == "live"
    assert result["meter_price_id"] is None
    line_items = fake_stripe.checkout_calls[0]["line_items"]
    assert len(line_items) == 1
    assert line_items[0]["quantity"] == 1
    assert line_items[0]["price_data"]["unit_amount"] == 14900
    assert line_items[0]["price_data"]["recurring"] == {"interval": "month"}


def test_checkout_enterprise_skips_metered_line_item(fresh_db, fake_stripe, db):
    # enterprise included_minutes == 0 (unmetered): metered price configured
    # but must NOT be attached.
    result = billing_service.create_checkout_session(
        db, TENANT_A, "enterprise", "https://app.voxflow.ai/success", "https://app.voxflow.ai/cancel")

    assert result["meter_price_id"] is None
    assert fake_stripe.checkout_calls[0]["line_items"] == [{"price": LIC_ENTERPRISE, "quantity": 1}]


def test_checkout_sandbox_mode_needs_no_network(fresh_db, fake_stripe, db, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    get_settings.cache_clear()

    result = billing_service.create_checkout_session(
        db, TENANT_A, "starter", "https://app.voxflow.ai/success", "https://app.voxflow.ai/cancel")

    assert result["mode"] == "sandbox"
    assert "sandbox_session=" in result["checkout_url"]
    assert result["meter_price_id"] == MET_STARTER
    assert fake_stripe.checkout_calls == []  # no Stripe call made
