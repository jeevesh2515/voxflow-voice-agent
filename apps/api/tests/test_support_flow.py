"""Tests for the inbound customer-support call flow.

Covers the parts a real caller exercises: two-factor identity verification,
PO/order lookups, and the structured outcome log that lands in Google Sheets.

The verification tests matter most — they are the boundary that stops one
company's caller reading another company's order book.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from voxflow_api.integrations.gsheets import GoogleSheetsClient
from voxflow_api.agent import tools
from voxflow_api.agent.tools import _KNOWLEDGE_BINDING_KEY
from voxflow_api.db import (
    Order,
    Shipment,
    Supplier,
    Tenant,
    init_db,
    session_scope,
)
from voxflow_api.voice.pipeline import CallSession


TENANT = "acme-support"
OTHER_TENANT = "rival-corp"


def _utc(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


@pytest.fixture(scope="module", autouse=True)
def seed_support_data():
    """Two tenants with their own customers and orders, so cross-tenant
    isolation can actually be tested rather than assumed."""
    init_db()
    with session_scope() as db:
        for tid, name in ((TENANT, "Acme Foods"), (OTHER_TENANT, "Rival Corp")):
            if not db.get(Tenant, tid):
                db.add(Tenant(id=tid, name=name))

        if not db.get(Supplier, "cust-1"):
            db.add(
                Supplier(
                    id="cust-1",
                    tenant_id=TENANT,
                    name="Varun Beverages Pvt Ltd",
                    phone="+919876500001",
                    city="Gurgaon",
                    state="Haryana",
                    pincode="122001",
                    contact_person="Rakesh Kumar",
                    gstin="06AABCV1234M1Z5",
                    contact_type="customer",
                )
            )
        # Same phone shape, different tenant — must never be reachable from TENANT.
        if not db.get(Supplier, "cust-2"):
            db.add(
                Supplier(
                    id="cust-2",
                    tenant_id=OTHER_TENANT,
                    name="Competitor Foods",
                    phone="+919876500002",
                    city="Mumbai",
                    state="Maharashtra",
                    pincode="400001",
                    contact_person="Someone Else",
                    gstin="27AAAAA0000A1Z1",
                    contact_type="customer",
                )
            )

        if not db.get(Order, "PO-SIGNED-1"):
            db.add(
                Order(
                    id="PO-SIGNED-1",
                    tenant_id=TENANT,
                    supplier_id="cust-1",
                    status="shipped",
                    items_json=json.dumps([{"sku": "PEP-250", "quantity": 500}]),
                    total_qty=500,
                    customer_po_ref="VB/PO/2026/0912",
                    po_signed=1,
                    po_signed_at=_utc(14),
                    po_signed_by="Anita Desai",
                    dispatched_at=_utc(10),
                )
            )
        if not db.get(Order, "PO-UNSIGNED-1"):
            db.add(
                Order(
                    id="PO-UNSIGNED-1",
                    tenant_id=TENANT,
                    supplier_id="cust-1",
                    status="pending",
                    items_json=json.dumps([{"sku": "7UP-500", "quantity": 120}]),
                    total_qty=120,
                    customer_po_ref="VB/PO/2026/1001",
                    po_signed=0,
                )
            )
        # Belongs to the OTHER tenant.
        if not db.get(Order, "PO-RIVAL-1"):
            db.add(
                Order(
                    id="PO-RIVAL-1",
                    tenant_id=OTHER_TENANT,
                    supplier_id="cust-2",
                    status="shipped",
                    items_json=json.dumps([{"sku": "SECRET", "quantity": 999}]),
                    total_qty=999,
                    customer_po_ref="RIVAL/PO/1",
                    po_signed=1,
                )
            )
        if not db.get(Shipment, "SHP-1"):
            db.add(
                Shipment(
                    id="SHP-1",
                    tenant_id=TENANT,
                    order_id="PO-SIGNED-1",
                    status="in_transit",
                    carrier="Delhivery",
                    tracking_no="DL123456789",
                    expected_delivery=_utc(-2),
                    history_json=json.dumps(
                        [
                            {"at": "2026-07-23", "status": "dispatched", "location": "Gurgaon DC"},
                            {"at": "2026-07-25", "status": "in_transit", "location": "Ghaziabad Hub"},
                        ]
                    ),
                )
            )


def _session(verified: bool = False, supplier_id: str | None = "cust-1") -> CallSession:
    """Build a session, binding knowledge authorization to `supplier_id` when
    `verified=True` — simulating that `verify_caller` already succeeded for
    this exact contact, which is what the current fail-closed binding requires.
    """
    s = CallSession(call_id=f"test-{id(object())}", tenant_id=TENANT)
    s.supplier_id = supplier_id
    s.verified = verified
    s.caller_phone = "+919876500001"
    if verified and supplier_id:
        s.route_policy[_KNOWLEDGE_BINDING_KEY] = supplier_id
    return s


# --------------------------------------------------------------- verification


def test_verify_requires_both_company_and_a_detail():
    """Company alone is not enough — that is single-factor."""
    s = _session()
    r = asyncio.run(tools.verify_caller(s, company="Varun Beverages"))
    assert r["verified"] is False
    assert s.verified is False
    assert "city_or_gstin_or_name" in r["missing"]


def test_verify_succeeds_with_company_and_city():
    s = _session()
    r = asyncio.run(tools.verify_caller(s, company="Varun Beverages", city_or_gstin="Gurgaon"))
    assert r["verified"] is True
    assert r["matched_on"] == "city"
    assert s.verified is True
    assert s.company_name == "Varun Beverages Pvt Ltd"


def test_verify_tolerates_speech_to_text_noise():
    """'Pvt. Ltd.' vs 'Pvt Ltd' and spaced-out GSTINs must not lock out a real caller."""
    s = _session()
    r = asyncio.run(
        tools.verify_caller(
            s, company="varun beverages pvt. ltd.", city_or_gstin="06 AABCV 1234 M1Z5"
        )
    )
    assert r["verified"] is True
    assert r["matched_on"] == "gstin"


def test_verify_accepts_contact_name_as_the_second_factor():
    s = _session()
    r = asyncio.run(
        tools.verify_caller(s, company="Varun Beverages", contact_name="Rakesh Kumar")
    )
    assert r["verified"] is True
    assert r["matched_on"] == "contact_name"


def test_verify_rejects_wrong_company():
    s = _session()
    r = asyncio.run(tools.verify_caller(s, company="Totally Different Ltd", city_or_gstin="Gurgaon"))
    assert r["verified"] is False
    assert s.verified is False


def test_verify_locks_out_after_three_attempts_and_escalates():
    """A caller fishing for someone else's data gets cut off, not endless retries."""
    s = _session()
    for _ in range(3):
        asyncio.run(tools.verify_caller(s, company="Wrong Co", city_or_gstin="Nowhere"))

    r = asyncio.run(tools.verify_caller(s, company="Varun Beverages", city_or_gstin="Gurgaon"))
    assert r["verified"] is False
    assert r["locked"] is True
    assert s.escalated is True


def test_verify_fails_when_caller_was_never_identified():
    s = _session(supplier_id=None)
    r = asyncio.run(tools.verify_caller(s, company="Varun Beverages", city_or_gstin="Gurgaon"))
    assert r["verified"] is False
    assert r["reason"] == "caller_not_identified"


# ------------------------------------------------------------- the data gate


def test_po_status_blocked_before_verification():
    """The whole point of verification: no order data leaks without it."""
    s = _session(verified=False)
    r = asyncio.run(tools.check_po_status(s, order_id="PO-SIGNED-1"))
    assert r["ok"] is False
    assert r["error"] == "not_verified"
    assert "total_qty" not in r


def test_order_details_blocked_before_verification():
    s = _session(verified=False)
    r = asyncio.run(tools.get_order_details(s, order_id="PO-SIGNED-1"))
    assert r["ok"] is False
    assert r["error"] == "not_verified"


# ------------------------------------------------------------------ PO status


def test_check_po_status_reports_a_signed_po():
    s = _session(verified=True)
    r = asyncio.run(tools.check_po_status(s, order_id="PO-SIGNED-1"))
    assert r["ok"] is True
    assert r["po_signed"] is True
    assert r["po_signed_by"] == "Anita Desai"
    assert r["total_qty"] == 500
    assert r["po_signed_at"] is not None


def test_check_po_status_reports_an_unsigned_po():
    s = _session(verified=True)
    r = asyncio.run(tools.check_po_status(s, order_id="PO-UNSIGNED-1"))
    assert r["ok"] is True
    assert r["po_signed"] is False
    assert r["po_signed_at"] is None


def test_check_po_status_by_customer_reference():
    """Callers quote their own PO number, not our internal ID."""
    s = _session(verified=True)
    r = asyncio.run(tools.check_po_status(s, customer_po_ref="VB/PO/2026/0912"))
    assert r["ok"] is True
    assert r["order_id"] == "PO-SIGNED-1"


def test_check_po_status_needs_a_reference():
    s = _session(verified=True)
    r = asyncio.run(tools.check_po_status(s))
    assert r["ok"] is False
    assert r["error"] == "no_reference"


# --------------------------------------------------------------- order detail


def test_get_order_details_includes_dispatch_and_current_location():
    """'When did you send it and where has it reached?' in one tool call."""
    s = _session(verified=True)
    r = asyncio.run(tools.get_order_details(s, order_id="PO-SIGNED-1"))
    assert r["ok"] is True
    assert r["dispatched_at"] is not None
    assert r["total_qty"] == 500
    ship = r["shipment"]
    assert ship["status"] == "in_transit"
    assert ship["carrier"] == "Delhivery"
    # Current location comes from the latest history entry.
    assert ship["current_location"] == "Ghaziabad Hub"


def test_get_order_details_handles_an_order_with_no_shipment():
    s = _session(verified=True)
    r = asyncio.run(tools.get_order_details(s, order_id="PO-UNSIGNED-1"))
    assert r["ok"] is True
    assert r["shipment"] is None


# ------------------------------------------------------- tenant/caller scoping


def test_cannot_read_another_tenants_order():
    """A verified caller must not reach another tenant's order by guessing an ID."""
    s = _session(verified=True)
    r = asyncio.run(tools.check_po_status(s, order_id="PO-RIVAL-1"))
    assert r["ok"] is False
    assert r["error"] == "not_found"


def test_cannot_read_another_customers_order_within_the_same_tenant():
    """Scoping is per contact, not just per tenant.

    Authorization is bound to the exact supplier that passed `verify_caller`.
    Manually reassigning `supplier_id` without a fresh verification for that
    contact must not be treated as still-verified — it must fail closed
    rather than fall through to a tenant-scoped lookup.
    """
    s = _session(verified=True)
    s.supplier_id = "cust-2"  # a different customer, never verified on this session
    r = asyncio.run(tools.check_po_status(s, order_id="PO-SIGNED-1"))
    assert r["ok"] is False
    assert r["error"] == "not_verified"


# --------------------------------------------------------------- outcome log


def test_log_call_outcome_records_structured_fields():
    s = _session(verified=True)
    s.company_name = "Varun Beverages Pvt Ltd"
    r = asyncio.run(
        tools.log_call_outcome(
            s,
            reason="Asked whether PO VB/PO/2026/0912 was signed",
            solution="Confirmed signed on 19 July, 500 cases, in transit",
            resolution_status="resolved",
            satisfaction="happy",
            related_order="PO-SIGNED-1",
        )
    )
    assert r["ok"] is True
    assert s.resolution_status == "resolved"
    assert s.satisfaction == "happy"
    assert s.outcome == "resolved"
    assert s.related_order == "PO-SIGNED-1"
    assert s.reason.startswith("Asked whether")


def test_log_call_outcome_coerces_invalid_enum_values():
    """A hallucinated status must not poison the ops dashboard."""
    s = _session(verified=True)
    r = asyncio.run(
        tools.log_call_outcome(
            s,
            reason="x",
            solution="y",
            resolution_status="kind-of-sorted",
            satisfaction="ecstatic",
        )
    )
    assert r["resolution_status"] == "partial"
    assert r["satisfaction"] == "neutral"


def test_log_call_outcome_survives_sheets_being_unavailable():
    """Google Sheets being down must never fail a live call."""
    s = _session(verified=True)
    r = asyncio.run(
        tools.log_call_outcome(
            s, reason="x", solution="y", resolution_status="resolved", satisfaction="happy"
        )
    )
    # Sheets is disabled in tests, so the row didn't sync...
    assert r["sheet_synced"] is False
    # ...but the tool still reports success and the session still holds the data.
    assert r["ok"] is True
    assert s.resolution_status == "resolved"


def test_sheets_client_is_inert_when_unconfigured():
    from voxflow_api.integrations.gsheets import get_sheets_client

    result = asyncio.run(get_sheets_client().append_call_outcome({"call_id": "x"}))
    assert result["ok"] is False
    assert result["reason"] == "sheets_not_configured"


# ------------------------------------------------------------ abandoned calls


def test_abandoned_call_still_produces_an_outcome():
    """A caller who hangs up mid-verification must not vanish from the log."""
    from voxflow_api.voice.pipeline import VoicePipeline

    s = _session()
    pipeline = VoicePipeline.__new__(VoicePipeline)  # skip __init__ (loads STT/LLM)
    asyncio.run(pipeline._log_abandoned_if_needed(s))

    assert s.resolution_status == "unresolved"
    assert s.outcome == "abandoned"
    assert s.follow_up_required is True
    assert s.reason  # a human-readable reason was filled in


def test_completed_call_outcome_is_not_overwritten_by_the_fallback():
    from voxflow_api.voice.pipeline import VoicePipeline

    s = _session(verified=True)
    asyncio.run(
        tools.log_call_outcome(
            s, reason="real reason", solution="real solution",
            resolution_status="resolved", satisfaction="happy",
        )
    )
    pipeline = VoicePipeline.__new__(VoicePipeline)
    asyncio.run(pipeline._log_abandoned_if_needed(s))

    assert s.resolution_status == "resolved"
    assert s.reason == "real reason"


# ------------------------------------------------------------ tool registration


def test_every_declared_tool_is_dispatchable():
    """A tool the LLM can see but the dispatcher can't route is a silent dead end."""
    declared = {t["function"]["name"] for t in tools.TOOL_DEFINITIONS}
    for name in declared:
        assert hasattr(tools, name), f"{name} is declared but has no implementation"

    s = _session()
    result = asyncio.run(tools.execute_tool("no_such_tool", {}, s))
    assert result["ok"] is False
    assert "unknown_tool" in result["error"]


def test_new_support_tools_are_declared_to_the_llm():
    declared = {t["function"]["name"] for t in tools.TOOL_DEFINITIONS}
    assert {"check_po_status", "get_order_details", "log_call_outcome"} <= declared


# ------------------------------------------------------- dashboard API surface


def test_calls_api_exposes_the_new_outcome_fields():
    """The dashboard can only render what the API actually returns."""
    from fastapi.testclient import TestClient

    from voxflow_api.db import Call
    from voxflow_api.main import create_app

    with session_scope() as db:
        if not db.get(Call, "call-api-1"):
            db.add(
                Call(
                    id="call-api-1",
                    tenant_id=TENANT,
                    caller_phone="+919876500001",
                    caller_name="Rakesh Kumar",
                    reason="Checked PO signing status",
                    solution="Confirmed signed, 500 cases",
                    resolution_status="resolved",
                    satisfaction="happy",
                    follow_up_required=0,
                    verified=1,
                    escalated=0,
                )
            )

    client = TestClient(create_app())
    r = client.get(f"/api/calls?tenant_id={TENANT}&limit=100")
    assert r.status_code == 200

    row = next((c for c in r.json() if c["id"] == "call-api-1"), None)
    assert row is not None, "seeded call not returned by /api/calls"
    for field in (
        "reason",
        "solution",
        "resolution_status",
        "satisfaction",
        "follow_up_required",
        "staff_resolution",
        "verified",
        "sheet_synced",
    ):
        assert field in row, f"/api/calls is missing {field}"
    assert row["resolution_status"] == "resolved"
    assert row["satisfaction"] == "happy"
    assert row["verified"] is True


def test_staff_can_record_a_resolution():
    from fastapi.testclient import TestClient

    from voxflow_api.db import Call
    from voxflow_api.main import create_app

    with session_scope() as db:
        if not db.get(Call, "call-esc-1"):
            db.add(
                Call(
                    id="call-esc-1",
                    tenant_id=TENANT,
                    caller_phone="+919876500001",
                    reason="Disputed short delivery",
                    resolution_status="unresolved",
                    satisfaction="unhappy",
                    follow_up_required=1,
                    escalated=1,
                )
            )

    client = TestClient(create_app())
    r = client.patch(
        "/api/calls/call-esc-1/resolution?tenant_id=acme-support",
        json={"staff_resolution": "Called back; 200 missing cases dispatched on 3 Aug."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["staff_resolution"].startswith("Called back")
    assert body["staff_resolved_at"] is not None


def test_resolution_patch_404s_for_an_unknown_call():
    from fastapi.testclient import TestClient

    from voxflow_api.main import create_app

    client = TestClient(create_app())
    r = client.patch("/api/calls/does-not-exist/resolution", json={"staff_resolution": "x"})
    assert r.status_code == 404


def test_resolution_patch_rejects_a_tenant_mismatch():
    from fastapi.testclient import TestClient

    from voxflow_api.main import create_app

    client = TestClient(create_app())
    r = client.patch(
        f"/api/calls/call-esc-1/resolution?tenant_id={OTHER_TENANT}",
        json={"staff_resolution": "should not apply"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------- non-blocking Sheets


def test_outcome_logging_does_not_block_the_caller_on_a_slow_sheet():
    """The single worst failure mode this product can have is dead air.

    log_call_outcome runs while the caller is still on the line. If Google is
    slow, the caller must NOT hear the delay — the write goes to a background
    task instead.
    """
    import asyncio as aio
    import time as _time

    from voxflow_api.integrations import gsheets

    SLOW = 3.0  # seconds Google "takes"

    class _SlowSheets:
        @staticmethod
        def is_configured() -> bool:
            return True

        @staticmethod
        async def append_call_outcome(row):
            await aio.sleep(SLOW)
            return {"ok": True, "updated_range": "Call Log!A2"}

    async def scenario():
        s = _session(verified=True)
        t0 = _time.perf_counter()
        result = await tools.log_call_outcome(
            s, reason="slow sheet", solution="x",
            resolution_status="resolved", satisfaction="happy",
        )
        elapsed = _time.perf_counter() - t0
        return s, result, elapsed

    original = gsheets.get_sheets_client
    tools_original = tools.get_sheets_client
    gsheets.get_sheets_client = lambda: _SlowSheets()      # type: ignore[assignment]
    tools.get_sheets_client = lambda: _SlowSheets()        # type: ignore[assignment]
    try:
        s, result, elapsed = asyncio.run(scenario())
    finally:
        gsheets.get_sheets_client = original               # type: ignore[assignment]
        tools.get_sheets_client = tools_original           # type: ignore[assignment]

    # The tool returned essentially immediately, NOT after SLOW seconds.
    assert elapsed < 1.0, f"caller waited {elapsed:.2f}s on Google — must be ~0"
    assert result["ok"] is True
    assert result["sheet_synced"] == "queued"
    assert result["sheet_job_id"].startswith("job-")
    # The outcome data is already safe on the session for Postgres.
    assert s.resolution_status == "resolved"
    assert s.satisfaction == "happy"


def test_end_session_drains_the_background_sheet_write():
    """After the caller hangs up, waiting is free — so sheet_synced becomes accurate."""
    from voxflow_api.voice.pipeline import VoicePipeline

    async def scenario():
        s = _session(verified=True)
        s.resolution_status = "resolved"  # pretend the outcome was logged

        async def slow_ok():
            await asyncio.sleep(0.05)
            return {"ok": True, "updated_range": "Call Log!A9"}

        s.sheet_task = asyncio.create_task(slow_ok())
        pipeline = VoicePipeline.__new__(VoicePipeline)
        await pipeline._drain_sheet_task(s)
        return s

    s = asyncio.run(scenario())
    assert s.sheet_synced is True
    assert s.sheet_task is None


def test_end_session_gives_up_on_a_hung_sheet_write_without_hanging():
    """A wedged Google request must not hold the call session open forever."""
    from voxflow_api.voice.pipeline import VoicePipeline

    async def scenario():
        s = _session(verified=True)

        async def never_returns():
            await asyncio.sleep(60)
            return {"ok": True}

        s.sheet_task = asyncio.create_task(never_returns())
        pipeline = VoicePipeline.__new__(VoicePipeline)
        import time as _t
        t0 = _t.perf_counter()
        await pipeline._drain_sheet_task(s, timeout=0.2)
        return s, _t.perf_counter() - t0

    s, elapsed = asyncio.run(scenario())
    assert elapsed < 2.0, f"drain took {elapsed:.2f}s — the timeout did not hold"
    # Not synced, but recorded as such: the row is still in Postgres.
    assert s.sheet_synced is False


def test_drain_is_a_noop_when_sheets_is_disabled():
    from voxflow_api.voice.pipeline import VoicePipeline

    s = _session(verified=True)
    assert s.sheet_task is None
    pipeline = VoicePipeline.__new__(VoicePipeline)
    asyncio.run(pipeline._drain_sheet_task(s))
    assert s.sheet_synced is False


# ── Google Sheets A1 notation ──────────────────────────────────────────────
# The default tab is "Call Log". The space makes `Call Log!A1` unparseable, and
# Google reports it as `400 Unable to parse range`, which reads like a missing
# sheet or a permissions problem and is neither. It silently broke every call
# outcome write.

@pytest.mark.parametrize(
    "tab,expected",
    [
        ("Call Log", "'Call Log'!A1"),      # the default — the one that broke
        ("Calls 2026", "'Calls 2026'!A1"),
        ("Log-A", "'Log-A'!A1"),            # hyphen is not alphanumeric
        ("O'Brien", "'O''Brien'!A1"),       # internal quote doubles
        ("Sheet1", "Sheet1!A1"),            # bare token needs no quoting
        ("Call_Log", "Call_Log!A1"),        # underscore is safe in A1
    ],
)
def test_a1_quoting(tab: str, expected: str) -> None:
    assert GoogleSheetsClient._a1(tab, "A1") == expected


def test_a1_used_for_both_read_and_append() -> None:
    """Quoting one call site and not the other is the obvious way to half-fix this."""
    import inspect

    src = inspect.getsource(GoogleSheetsClient)
    assert 'f"{tab}!A1:Z1"' not in src, "header range bypasses _a1()"
    assert "{tab}!A1:append" not in src, "append range bypasses _a1()"
    assert src.count("self._a1(") >= 2


def test_send_sms_tool_execution():
    """Verify send_sms queues a durable notification without direct IO."""
    s = _session(verified=True)
    res = asyncio.run(
        tools.execute_tool(
            "send_sms",
            {"to_phone": "9876500001", "message": "Your PO-SIGNED-1 has been verified."},
            s,
        )
    )
    assert res["ok"] is True
    assert res["channel"] == "sms"
    assert res["recipient"] == "+9876500001"
    assert res["comm_id"].startswith("comm-sms-")
    assert res["status"] == "queued"
    assert res["job_id"].startswith("job-")
