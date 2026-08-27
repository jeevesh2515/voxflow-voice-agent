"""Regression tests for contact-bound caller authorization."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest

from voxflow_api.agent.tools import (
    check_po_status,
    create_po,
    get_order_details,
    get_shipment_status,
    lookup_supplier,
    verify_caller,
    verify_pin,
    verify_po,
)
from voxflow_api.cache import supplier_cache
from voxflow_api.db import Order, Shipment, Supplier, Tenant, session_scope
from voxflow_api.voice.pipeline import CallSession


TENANT_ID = "authorization-binding"
SUPPLIER_A = "authorization-supplier-a"
SUPPLIER_B = "authorization-supplier-b"
ORDER_A = "AUTH-PO-A"
ORDER_B = "AUTH-PO-B"
SHIPMENT_A = "AUTH-SHIP-A"
SHIPMENT_B = "AUTH-SHIP-B"


@pytest.fixture
def authorization_records() -> Iterator[None]:
    supplier_cache.clear()
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.query(Shipment).filter(Shipment.tenant_id == TENANT_ID).delete()
        db.query(Order).filter(Order.tenant_id == TENANT_ID).delete()
        db.query(Supplier).filter(Supplier.tenant_id == TENANT_ID).delete()
        if not db.get(Tenant, TENANT_ID):
            db.add(Tenant(id=TENANT_ID, name="Authorization Binding Tests"))
            db.flush()
        db.add_all(
            [
                Supplier(
                    id=SUPPLIER_A,
                    tenant_id=TENANT_ID,
                    name="Alpha Supplies",
                    phone="+919100000001",
                    city="Pune",
                    state="Maharashtra",
                    pincode="411001",
                    contact_person="Asha Rao",
                    gstin="27ALPHA0000A1Z5",
                    auth_pin="1111",
                ),
                Supplier(
                    id=SUPPLIER_B,
                    tenant_id=TENANT_ID,
                    name="Beta Supplies",
                    phone="+919100000002",
                    city="Indore",
                    state="Madhya Pradesh",
                    pincode="452001",
                    contact_person="Bina Shah",
                    gstin="23BETA00000B1Z5",
                    auth_pin="2222",
                ),
            ]
        )
        db.flush()
        db.add_all(
            [
                Order(
                    id=ORDER_A,
                    tenant_id=TENANT_ID,
                    supplier_id=SUPPLIER_A,
                    status="shipped",
                    items_json=json.dumps([{"sku": "ALPHA-SKU", "quantity": 10}]),
                    total_qty=10,
                    customer_po_ref="ALPHA/PO/1",
                    po_signed=1,
                ),
                Order(
                    id=ORDER_B,
                    tenant_id=TENANT_ID,
                    supplier_id=SUPPLIER_B,
                    status="shipped",
                    items_json=json.dumps([{"sku": "BETA-SECRET", "quantity": 99}]),
                    total_qty=99,
                    customer_po_ref="BETA/PO/1",
                    po_signed=1,
                ),
            ]
        )
        db.flush()
        db.add_all(
            [
                Shipment(
                    id=SHIPMENT_A,
                    tenant_id=TENANT_ID,
                    order_id=ORDER_A,
                    status="in_transit",
                    carrier="Alpha Carrier",
                    tracking_no="TRACK-ALPHA",
                    last_update=now - timedelta(hours=1),
                ),
                Shipment(
                    id=SHIPMENT_B,
                    tenant_id=TENANT_ID,
                    order_id=ORDER_B,
                    status="out_for_delivery",
                    carrier="Beta Carrier",
                    tracking_no="TRACK-BETA-SECRET",
                    last_update=now,
                ),
            ]
        )

    yield

    supplier_cache.clear()
    with session_scope() as db:
        db.query(Shipment).filter(Shipment.tenant_id == TENANT_ID).delete()
        db.query(Order).filter(Order.tenant_id == TENANT_ID).delete()
        db.query(Supplier).filter(Supplier.tenant_id == TENANT_ID).delete()
        tenant = db.get(Tenant, TENANT_ID)
        if tenant:
            db.delete(tenant)


def _session(*, mode: str = "standard") -> CallSession:
    return CallSession(
        call_id="authorization-binding-call",
        tenant_id=TENANT_ID,
        verification_mode=mode,
    )


async def _verify_supplier_a(session: CallSession, *, pin: bool = False) -> None:
    found = await lookup_supplier(session, phone="+919100000001")
    assert found["id"] == SUPPLIER_A
    knowledge = await verify_caller(
        session,
        company="Alpha Supplies",
        city_or_gstin="Pune",
    )
    assert knowledge["verified"] is True
    if pin:
        pin_result = await verify_pin(session, pin="1111")
        assert pin_result["verified"] is True


@pytest.mark.asyncio
async def test_unverified_order_and_shipment_reads_are_denied(authorization_records: None) -> None:
    session = _session()
    await lookup_supplier(session, phone="+919100000001")

    results = [
        await get_shipment_status(session, order_id=ORDER_A),
        await verify_po(session, order_id=ORDER_A),
        await check_po_status(session, order_id=ORDER_A),
        await get_order_details(session, order_id=ORDER_A),
    ]

    assert all(result.get("error") == "not_verified" for result in results)
    assert all("tracking_no" not in result and "total_qty" not in result for result in results)


@pytest.mark.asyncio
async def test_unbound_authorization_flags_do_not_grant_access(authorization_records: None) -> None:
    session = _session(mode="enhanced")
    session.supplier_id = SUPPLIER_A
    session.verified = True
    session.pin_verified = True

    read = await get_shipment_status(session, order_id=ORDER_A)
    write = await create_po(session, items=[{"sku": "ALPHA-SKU", "quantity": 1}])

    assert read["error"] == "not_verified"
    assert write["error"] == "pin_required"


@pytest.mark.asyncio
async def test_verification_is_cleared_when_lookup_switches_or_becomes_unresolved(
    authorization_records: None,
) -> None:
    session = _session()
    await _verify_supplier_a(session, pin=True)

    switched = await lookup_supplier(session, phone="+919100000002")
    assert switched["id"] == SUPPLIER_B
    assert session.supplier_id == SUPPLIER_B
    assert session.verified is False
    assert session.pin_verified is False
    assert (await get_shipment_status(session, order_id=ORDER_B))["error"] == "not_verified"

    session.verified = True
    session.pin_verified = True
    unresolved = await lookup_supplier(session, phone="not a real phone")
    assert unresolved["found"] is False
    assert session.supplier_id is None
    assert session.verified is False
    assert session.pin_verified is False


@pytest.mark.asyncio
async def test_supplier_a_authorization_cannot_target_supplier_b(authorization_records: None) -> None:
    session = _session()
    await _verify_supplier_a(session, pin=True)

    latest = await get_shipment_status(session)
    assert latest["shipment_id"] == SHIPMENT_A
    assert latest["tracking_no"] == "TRACK-ALPHA"
    assert (await get_shipment_status(session, order_id=ORDER_B))["found"] is False
    assert (await verify_po(session, order_id=ORDER_B))["error"] == "not_found"
    assert (await check_po_status(session, order_id=ORDER_B))["error"] == "not_found"

    mismatched_write = await create_po(
        session,
        supplier_id=SUPPLIER_B,
        items=[{"sku": "BETA-SKU", "quantity": 1}],
    )
    assert mismatched_write["ok"] is False
    assert mismatched_write["error"] == "supplier_mismatch"


@pytest.mark.asyncio
async def test_enhanced_reads_require_bound_knowledge_and_pin(authorization_records: None) -> None:
    session = _session(mode="enhanced")
    await _verify_supplier_a(session)

    without_pin = await get_shipment_status(session, order_id=ORDER_A)
    assert without_pin["error"] == "pin_required"

    assert (await verify_pin(session, pin="1111"))["verified"] is True
    authorized = await get_shipment_status(session, order_id=ORDER_A)
    assert authorized["shipment_id"] == SHIPMENT_A


@pytest.mark.asyncio
async def test_valid_same_contact_read_and_write_flow(authorization_records: None) -> None:
    session = _session()
    await _verify_supplier_a(session, pin=True)

    shipment = await get_shipment_status(session, order_id=ORDER_A)
    po = await verify_po(session, order_id=ORDER_A)
    created = await create_po(session, items=[{"sku": "ALPHA-SKU", "quantity": 3}])

    assert shipment["shipment_id"] == SHIPMENT_A
    assert po["ok"] is True and po["total_qty"] == 10
    assert created["ok"] is True
    assert created["supplier_id"] == SUPPLIER_A
