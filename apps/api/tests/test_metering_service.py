"""Tests for per-call-minute usage metering and Stripe Billing Meters integration."""

from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from voxflow_api.config import get_settings
from voxflow_api.db import Call, Tenant, reset_db, session_scope
from voxflow_api.seed import seed
from voxflow_api.services.metering_service import (
    _resolve_stripe_customer,
    billed_minutes_for,
    meter_all_tenants,
    meter_calls_for_tenant,
    meter_event_identifier,
)
from voxflow_api.services.retry import classify_error, is_transient_error, retry_transient


# =====================================================================
# 1. Rounding & Identifier Unit Tests
# =====================================================================


def test_billed_minutes_rounding_rules():
    # Minimum 1 minute for any completed call with positive duration
    assert billed_minutes_for(1) == 1
    assert billed_minutes_for(30) == 1
    assert billed_minutes_for(59) == 1
    assert billed_minutes_for(60) == 1

    # Ceil to next minute
    assert billed_minutes_for(61) == 2
    assert billed_minutes_for(90) == 2
    assert billed_minutes_for(120) == 2
    assert billed_minutes_for(121) == 3
    assert billed_minutes_for(300) == 5

    # Fallback to wall-clock window when duration_sec is 0
    t0 = datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=90)
    assert billed_minutes_for(0, started_at=t0, ended_at=t1) == 1

    t2 = t0 + timedelta(seconds=150)
    assert billed_minutes_for(0, started_at=t0, ended_at=t2) == 2

    # Unbillable calls (duration 0 and no valid window) return 0
    assert billed_minutes_for(0) == 0
    assert billed_minutes_for(0, started_at=t0, ended_at=t0) == 0
    assert billed_minutes_for(-5) == 0


def test_meter_event_identifier_format():
    call_id = "call_abc123_456"
    ident = meter_event_identifier(call_id)
    assert ident == "voxflow-call-meter-call_abc123_456"
    assert len(ident) <= 100


def test_resolve_stripe_customer():
    t_with_id = Tenant(id="t1", name="T1", stripe_customer_id="cus_real123")
    assert _resolve_stripe_customer(t_with_id) == "cus_real123"

    t_empty = Tenant(id="t2", name="T2", stripe_customer_id="")
    assert _resolve_stripe_customer(t_empty) == ""


# =====================================================================
# 2. Retry & Classification Tests
# =====================================================================


def test_classify_error():
    class MockStripeError(Exception):
        def __init__(self, status):
            self.http_status = status

    # Transient
    assert classify_error(MockStripeError(429)) == "transient"
    assert classify_error(MockStripeError(500)) == "transient"
    assert classify_error(MockStripeError(503)) == "transient"
    assert classify_error(ConnectionError()) == "transient"
    assert classify_error(TimeoutError()) == "transient"
    assert classify_error(socket.timeout()) == "transient"
    assert classify_error(OSError()) == "transient"
    assert is_transient_error(MockStripeError(500)) is True

    # Permanent
    assert classify_error(MockStripeError(400)) == "permanent"
    assert classify_error(MockStripeError(401)) == "permanent"
    assert classify_error(MockStripeError(404)) == "permanent"
    assert is_transient_error(MockStripeError(404)) is False


def test_retry_transient_decorator():
    call_count = 0

    @retry_transient(tries=3, base_delay=0.01, max_delay=0.05, jitter=0.0)
    def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("reset")
        return "ok"

    assert flaky_func() == "ok"
    assert call_count == 3


# =====================================================================
# 3. Tenant Metering Service Tests
# =====================================================================


@pytest.fixture(autouse=True)
def init_clean_db():
    reset_db()
    seed(reset=True)


def test_meter_calls_for_tenant_dry_run():
    tenant_id = "test_meter_tenant"
    with session_scope() as db:
        tenant = Tenant(
            id=tenant_id,
            name="Test Meter Tenant",
            active=1,
            stripe_customer_id="cus_test_varun",
        )
        db.add(tenant)
        # Add test calls
        c1 = Call(
            id="call-meter-test-1",
            tenant_id=tenant_id,
            duration_sec=75,
            started_at=datetime.now(timezone.utc),
        )
        c2 = Call(
            id="call-meter-test-2",
            tenant_id=tenant_id,
            duration_sec=140,
            started_at=datetime.now(timezone.utc),
        )
        db.add_all([c1, c2])
        db.commit()

        # Execute dry-run
        res = meter_calls_for_tenant(db, tenant, dry_run=True)
        assert res["sent"] == 2
        assert res["skipped"] == 0

        # DB must NOT be marked billed in dry-run
        c1_refreshed = db.get(Call, "call-meter-test-1")
        assert c1_refreshed.metering_billed_at is None
        assert c1_refreshed.metering_event_id == ""


def test_meter_calls_for_tenant_live_execution(monkeypatch):
    tenant_id = "test_live_tenant"
    sent_events = []

    def fake_send_meter_event(*, event_name, identifier, payload, timestamp_unix):
        sent_events.append({
            "event_name": event_name,
            "identifier": identifier,
            "payload": payload,
            "timestamp_unix": timestamp_unix,
        })
        return {"id": f"evt_{identifier}"}

    monkeypatch.setattr("voxflow_api.services.metering_service._send_meter_event", fake_send_meter_event)

    with session_scope() as db:
        tenant = Tenant(
            id=tenant_id,
            name="Test Live Tenant",
            active=1,
            stripe_customer_id="cus_test_varun",
        )
        db.add(tenant)
        c1 = Call(
            id="call-meter-live-1",
            tenant_id=tenant_id,
            duration_sec=90,  # 2 minutes
            started_at=datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 9, 4, 10, 1, 30, tzinfo=timezone.utc),
        )
        db.add(c1)
        db.commit()

        res = meter_calls_for_tenant(db, tenant, dry_run=False)
        assert res["sent"] == 1
        assert res["skipped"] == 0

        # Verify event details sent
        assert len(sent_events) == 1
        evt = sent_events[0]
        assert evt["event_name"] == "voxflow_voice_minutes"
        assert evt["identifier"] == "voxflow-call-meter-call-meter-live-1"
        assert evt["payload"] == {"stripe_customer_id": "cus_test_varun", "value": 2}
        assert evt["timestamp_unix"] == int(datetime(2026, 9, 4, 10, 1, 30, tzinfo=timezone.utc).timestamp())

        # Verify DB marked
        c1_db = db.get(Call, "call-meter-live-1")
        assert c1_db.metering_billed_at is not None
        assert c1_db.metering_event_id == "voxflow-call-meter-call-meter-live-1"

        # Re-running immediately should send 0 because it's already billed (idempotency)
        res_repeat = meter_calls_for_tenant(db, tenant, dry_run=False)
        assert res_repeat["sent"] == 0


def test_meter_calls_for_tenant_missing_stripe_customer():
    tenant_id = "test_nocust_tenant"
    with session_scope() as db:
        tenant = Tenant(
            id=tenant_id,
            name="Test NoCust Tenant",
            active=1,
            stripe_customer_id="",
        )
        db.add(tenant)
        c1 = Call(
            id="call-meter-nocust-1",
            tenant_id=tenant_id,
            duration_sec=60,
            started_at=datetime.now(timezone.utc),
        )
        db.add(c1)
        db.commit()

        res = meter_calls_for_tenant(db, tenant, dry_run=False)
        assert res["sent"] == 0
        assert res["reason"] == "no_stripe_customer"

        # Call remains unbilled
        c1_db = db.get(Call, "call-meter-nocust-1")
        assert c1_db.metering_billed_at is None


def test_meter_all_tenants_batch(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_mock_123")

    sent_events = []

    def fake_send_meter_event(*, event_name, identifier, payload, timestamp_unix):
        sent_events.append({"identifier": identifier, "payload": payload})
        return {"id": "evt_ok"}

    monkeypatch.setattr("voxflow_api.services.metering_service._send_meter_event", fake_send_meter_event)

    tenant_id = "test_batch_tenant"
    with session_scope() as db:
        tenant = Tenant(
            id=tenant_id,
            name="Test Batch Tenant",
            active=1,
            stripe_customer_id="cus_varun_batch",
        )
        db.add(tenant)
        c1 = Call(
            id="call-batch-1",
            tenant_id=tenant_id,
            duration_sec=120,
            started_at=datetime.now(timezone.utc),
        )
        db.add(c1)
        db.commit()

        summary = meter_all_tenants(db, tenant_id=tenant_id, dry_run=False)
        assert summary["tenants"] == 1
        assert summary["sent"] == 1
        assert len(summary["errors"]) == 0
        assert len(sent_events) == 1
