"""Tests for Tier 2 Caller PIN Authentication and order creation security gating (Day 13)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from voxflow_api.agent.tools import create_po, lookup_supplier, verify_pin
from voxflow_api.cache import supplier_cache
from voxflow_api.db import Supplier, Tenant, async_session_scope, close_db_engines
from voxflow_api.voice.pipeline import CallSession


pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(loop_scope="module")
async def pin_supplier():
    """Create a test tenant and supplier with a known 4-digit PIN."""
    supplier_cache.clear()
    async with async_session_scope() as db:
        t = await db.get(Tenant, "t-pin")
        if not t:
            db.add(Tenant(id="t-pin", name="PIN Security Test Co"))
            await db.flush()

        sup = await db.get(Supplier, "s-pin-01")
        if not sup:
            db.add(
                Supplier(
                    id="s-pin-01",
                    tenant_id="t-pin",
                    name="Varun Beverages UK",
                    phone="+447460041934",
                    city="London",
                    state="Greater London",
                    pincode="EC1A 1BB",
                    contact_person="Rohan Sharma",
                    gstin="27AAACV1234A1Z5",
                    auth_pin="4321",
                )
            )
            await db.flush()
    yield
    supplier_cache.clear()
    await close_db_engines()


async def test_create_po_blocked_without_pin_auth(pin_supplier):
    """create_po must be blocked if session.pin_verified is False."""
    session = CallSession(call_id="call-pin-01", tenant_id="t-pin")
    # Identify supplier first
    found = await lookup_supplier(session, phone="+447460041934")
    assert found["found"] is True
    assert session.pin_verified is False

    # Attempt create_po before PIN verification
    res = await create_po(session, items=[{"sku": "PEP-250", "quantity": 10}])
    assert res["ok"] is False
    assert res["error"] == "pin_required"
    assert res["verified_pin"] is False


async def test_verify_pin_invalid_pin(pin_supplier):
    """verify_pin with incorrect PIN returns invalid_pin and increments attempts."""
    session = CallSession(call_id="call-pin-02", tenant_id="t-pin")
    await lookup_supplier(session, phone="+447460041934")

    res = await verify_pin(session, pin="9999")
    assert res["verified"] is False
    assert res["reason"] == "invalid_pin"
    assert session.pin_verified is False
    assert session.pin_attempts == 1


async def test_verify_pin_success(pin_supplier):
    """verify_pin with correct PIN sets session.pin_verified to True."""
    session = CallSession(call_id="call-pin-03", tenant_id="t-pin")
    await lookup_supplier(session, phone="+447460041934")

    res = await verify_pin(session, pin="4321")
    assert res["verified"] is True
    assert session.pin_verified is True


async def test_create_po_succeeds_after_pin_auth(pin_supplier):
    """create_po succeeds once session.pin_verified is True."""
    session = CallSession(call_id="call-pin-04", tenant_id="t-pin")
    await lookup_supplier(session, phone="+447460041934")

    # Step 1: Verify PIN
    res_pin = await verify_pin(session, pin="4321")
    assert res_pin["verified"] is True

    # Step 2: Call create_po
    res_po = await create_po(session, items=[{"sku": "PEP-250", "quantity": 50}])
    assert res_po["ok"] is True
    assert res_po["status"] == "pending"
    assert "order_id" in res_po


async def test_verify_pin_max_attempts_lockout(pin_supplier):
    """Exceeding 3 failed PIN attempts locks out and escalates the session."""
    session = CallSession(call_id="call-pin-05", tenant_id="t-pin")
    await lookup_supplier(session, phone="+447460041934")

    for _ in range(3):
        res = await verify_pin(session, pin="0000")
        assert res["verified"] is False

    # 4th attempt should lock out
    res_locked = await verify_pin(session, pin="4321")
    assert res_locked["verified"] is False
    assert res_locked["reason"] == "too_many_attempts"
    assert res_locked["locked"] is True
    assert session.escalated is True
