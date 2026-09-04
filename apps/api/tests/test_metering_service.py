"""Metering service tests: Stripe Billing Meter events from call minutes.

Drives metering_service through a recording fake Stripe client so every
assertion is offline and deterministic - no network, no real client, no
Stripe key. Mirrors repo conventions: plain test_* functions, autouse DB
reset, monkeypatch for env + Stripe module swap, SessionLocal/session_scope
from voxflow_api.db.
"""

from __future__ import annotations

from datetime import datetime, timezone
import socket

import pytest

from voxflow_api.config import get_settings
from voxflow_api.db import Call, SessionLocal, Tenant, reset_db, session_scope
from voxflow_api.services import billing_service, metering_service
from voxflow_api.services.retry import classify_error, is_transient_error, retry_transient


TENANT_A = "meter-alpha"
TENANT_B = "meter-beta"
CUSTOMER_A = "cus_meter_alpha"
CUSTOMER_B = "cus_meter_beta"


class StripeLikeError(Exception):
    """Mirrors the shape of stripe.error.*: carries http_status for the
    retry classifier in services/retry.py."""

    def __init__(self, http_status: int, message: str = "") -> None:
        super().__init__(message or f"stripe error {http_status}")
        self.http_status = http_status
        self.code = "fake_code"


class FakeMeterEvents:
    def __init__(self, fake: FakeStripeModule) -> None:
        self._fake = fake

    def create(self, **kwargs) -> dict:
        if self._fake.raise_status is not None:
            raise StripeLikeError(self._fake.raise_status)
        self._fake.events.append(kwargs)
        return {"id": f"mev_{len(self._fake.events)}", **kwargs}


class FakeStripeModule:
    """Recording double for stripe.billing.MeterEvent.create.

    Records every call (kwargs) and can be told to raise a StripeLikeError
    with a given http_status. Never touches the network.
    """

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.raise_status: int | None = None
        self.billing = type(
            "FakeBilling", (), {"MeterEvent": FakeMeterEvents(self)}
        )()


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    """Deterministic offline config + clean tables for every test."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_key")
    monkeypatch.setenv("STRIPE_METER_EVENT_NAME", "voxflow_voice_minutes")
    get_settings.cache_clear()
    reset_db()
    with session_scope() as db:
        db.add_all(
            [
                Tenant(
                    id=TENANT_A,
                    name="Alpha Logistics",
                    plan="starter",
                    active=1,
                    stripe_customer_id=CUSTOMER_A,
                ),
                Tenant(
                    id=TENANT_B,
                    name="Beta Freight",
                    plan="starter",
                    active=0,
                    stripe_customer_id=CUSTOMER_B,
                ),
            ]
        )


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def fake_stripe(monkeypatch):
    fake = FakeStripeModule()
    monkeypatch.setattr(billing_service, "_stripe_module", lambda: fake)
    monkeypatch.setattr("voxflow_api.services.retry.time.sleep", lambda _s: None)
    return fake


def _now() -> datetime:
    return datetime(2026, 9, 4, 10, 0, 0, tzinfo=timezone.utc)


def _call(
    call_id: str,
    tenant_id: str = TENANT_A,
    *,
    duration_sec: int = 90,
    ended: bool = True,
) -> None:
    with session_scope() as db:
        db.add(
            Call(
                id=call_id,
                tenant_id=tenant_id,
                started_at=_now(),
                ended_at=datetime(2026, 9, 4, 10, 1, 30, tzinfo=timezone.utc) if ended else None,
                duration_sec=duration_sec,
            )
        )


def test_classify_error():
    assert classify_error(StripeLikeError(429)) == "transient"
    assert classify_error(StripeLikeError(500)) == "transient"
    assert classify_error(StripeLikeError(503)) == "transient"
    assert classify_error(ConnectionError()) == "transient"
    assert classify_error(TimeoutError()) == "transient"
    assert classify_error(socket.timeout()) == "transient"
    assert classify_error(OSError()) == "transient"
    assert is_transient_error(StripeLikeError(500)) is True

    assert classify_error(StripeLikeError(400)) == "permanent"
    assert classify_error(StripeLikeError(401)) == "permanent"
    assert classify_error(StripeLikeError(404)) == "permanent"
    assert is_transient_error(StripeLikeError(404)) is False


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


def test_billed_minutes_rounds_up_to_whole_minutes_with_minimum_one():
    assert metering_service.billed_minutes_for(1) == 1
    assert metering_service.billed_minutes_for(59) == 1
    assert metering_service.billed_minutes_for(60) == 1
    assert metering_service.billed_minutes_for(61) == 2
    assert metering_service.billed_minutes_for(90) == 2
    assert metering_service.billed_minutes_for(3600) == 60


def test_billed_minutes_falls_back_to_wall_clock_window_only_when_duration_is_zero():
    start = _now()
    end_100s = datetime(2026, 9, 4, 10, 1, 40, tzinfo=timezone.utc)
    assert metering_service.billed_minutes_for(0, started_at=start, ended_at=end_100s) == 1
    assert metering_service.billed_minutes_for(0, started_at=start, ended_at=start) == 0
    assert metering_service.billed_minutes_for(-5) == 0
    assert metering_service.billed_minutes_for(0) == 0


def test_meter_event_identifier_is_stable_and_within_stripe_limit():
    assert metering_service.meter_event_identifier(TENANT_A) == f"voxflow-call-meter-{TENANT_A}"
    assert len(metering_service.meter_event_identifier("x" * 64)) <= 100


def test_sends_one_meter_event_per_call_with_exact_payload(fresh_db, fake_stripe, db):
    _call("call-1", duration_sec=90)   # ceil(90/60) = 2 minutes
    _call("call-2", duration_sec=1)    # minimum 1 minute
    _call("call-3", duration_sec=60, ended=False)  # no ended_at -> timestamp from started_at

    result = metering_service.meter_calls_for_tenant(db, db.get(Tenant, TENANT_A))

    assert result["sent"] == 3
    assert len(fake_stripe.events) == 3
    by_ident = {e["identifier"]: e for e in fake_stripe.events}
    assert set(by_ident) == {
        "voxflow-call-meter-call-1",
        "voxflow-call-meter-call-2",
        "voxflow-call-meter-call-3",
    }
    ev1 = by_ident["voxflow-call-meter-call-1"]
    assert ev1["event_name"] == "voxflow_voice_minutes"
    assert ev1["payload"] == {"stripe_customer_id": CUSTOMER_A, "value": 2}
    call1 = db.get(Call, "call-1")
    assert ev1["timestamp"] == int(call1.ended_at.timestamp())
    assert by_ident["voxflow-call-meter-call-2"]["payload"]["value"] == 1
    call3 = db.get(Call, "call-3")
    assert by_ident["voxflow-call-meter-call-3"]["timestamp"] == int(call3.started_at.timestamp())

    assert db.get(Call, "call-1").metering_billed_at is not None
    assert db.get(Call, "call-1").metering_event_id == "voxflow-call-meter-call-1"
    assert db.get(Call, "call-2").metering_billed_at is not None


def test_skips_calls_already_marked_billed(fresh_db, fake_stripe, db):
    _call("call-1", duration_sec=60)
    with session_scope() as sdb:
        sdb.get(Call, "call-1").metering_billed_at = datetime.now(timezone.utc)

    result = metering_service.meter_calls_for_tenant(db, db.get(Tenant, TENANT_A))

    assert result["sent"] == 0
    assert fake_stripe.events == []


def test_skips_tenant_without_resolvable_stripe_customer(fresh_db, fake_stripe, db):
    with session_scope() as sdb:
        sdb.add(
            Tenant(
                id="meter-none",
                name="No Stripe",
                plan="starter",
                active=1,
                stripe_customer_id="",
            )
        )
    _call("call-x", tenant_id="meter-none", duration_sec=30)

    result = metering_service.meter_calls_for_tenant(db, db.get(Tenant, "meter-none"))

    assert result["reason"] == "no_stripe_customer"
    assert result["sent"] == 0
    assert fake_stripe.events == []


def test_dry_run_reports_without_sending(fresh_db, fake_stripe, db):
    _call("call-1", duration_sec=120)

    result = metering_service.meter_calls_for_tenant(
        db, db.get(Tenant, TENANT_A), dry_run=True
    )

    assert result["sent"] == 1
    assert fake_stripe.events == []
    assert db.get(Call, "call-1").metering_billed_at is None


def test_transient_failure_raises_and_leaves_call_unbilled_for_next_run(
    fresh_db, fake_stripe, db
):
    fake_stripe.raise_status = 503  # transient -> retried 3x, then raised
    _call("call-1", duration_sec=60)

    with pytest.raises(StripeLikeError):
        metering_service.meter_calls_for_tenant(db, db.get(Tenant, TENANT_A))
    assert db.get(Call, "call-1").metering_billed_at is None

    fake_stripe.raise_status = None  # next scheduled run succeeds
    result = metering_service.meter_calls_for_tenant(db, db.get(Tenant, TENANT_A))
    assert result["sent"] == 1
    assert db.get(Call, "call-1").metering_billed_at is not None


def test_permanent_failure_is_skipped_not_marked_and_never_raises(
    fresh_db, fake_stripe, db
):
    fake_stripe.raise_status = 400  # permanent (bad meter name, wrong key)
    _call("call-1", duration_sec=60)

    result = metering_service.meter_calls_for_tenant(db, db.get(Tenant, TENANT_A))

    assert result["sent"] == 0
    assert result["skipped"] == 1
    assert db.get(Call, "call-1").metering_billed_at is None


def test_meter_all_tenants_only_processes_active_tenants(fresh_db, fake_stripe, db):
    _call("call-1", tenant_id=TENANT_A, duration_sec=60)   # active
    _call("call-2", tenant_id=TENANT_B, duration_sec=120)  # inactive -> omitted

    summary = metering_service.meter_all_tenants(db)

    assert summary["tenants"] == 1
    assert summary["sent"] == 1
    assert summary["errors"] == []
    assert len(fake_stripe.events) == 1
    assert fake_stripe.events[0]["payload"]["stripe_customer_id"] == CUSTOMER_A


def test_meter_all_tenants_skips_when_not_live_mode(fresh_db, fake_stripe, db, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    get_settings.cache_clear()
    _call("call-1", duration_sec=60)

    summary = metering_service.meter_all_tenants(db)

    assert summary.get("note") == "sandbox_mode"
    assert summary["sent"] == 0
    assert fake_stripe.events == []


def test_stripe_calls_go_through_the_fake_not_a_real_client(fresh_db, fake_stripe, db):
    _call("call-1", duration_sec=60)

    metering_service.meter_calls_for_tenant(db, db.get(Tenant, TENANT_A))

    assert fake_stripe.events
    assert billing_service._stripe_module() is fake_stripe



