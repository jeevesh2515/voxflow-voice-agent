"""Regression tests for the persistent, cross-session caller-PIN lockout.

A `CallSession`-scoped attempt counter alone cannot stop brute forcing across
many fresh calls: every new call, and every unauthenticated `/agent/run`
request, starts a brand-new session with zero attempts. These tests prove the
lockout stored on the `Supplier` row itself survives across sessions, expires
after its window, resets on success, and can be cleared by an owner PIN reset.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from voxflow_api import auth
from voxflow_api.agent.tools import (
    PERSISTENT_MAX_FAILED_PIN_ATTEMPTS,
    lookup_supplier,
    verify_pin,
)
from voxflow_api.auth import AuthUser, normalized_email_hash
from voxflow_api.cache import supplier_cache
from voxflow_api.config import get_settings
from voxflow_api.db import Supplier, Tenant, TenantMember, session_scope
from voxflow_api.main import create_app
from voxflow_api.services.pin_security import hash_pin, verify_pin_hash
from voxflow_api.voice.pipeline import CallSession


TENANT_ID = "pin-lockout-tenant"
SUPPLIER_ID = "pin-lockout-supplier"
CORRECT_PIN = "9876"
WRONG_PIN = "0000"


@pytest.fixture
def lockout_supplier() -> Iterator[None]:
    supplier_cache.clear()
    with session_scope() as db:
        db.query(Supplier).filter(Supplier.tenant_id == TENANT_ID).delete()
        if not db.get(Tenant, TENANT_ID):
            db.add(Tenant(id=TENANT_ID, name="PIN Lockout Test Co"))
            db.flush()
        db.add(
            Supplier(
                id=SUPPLIER_ID,
                tenant_id=TENANT_ID,
                name="Lockout Supplier",
                phone="+919200000001",
                city="Chennai",
                state="Tamil Nadu",
                pincode="600001",
                contact_person="Locked Contact",
                gstin="33LOCK00000L1Z5",
                auth_pin_hash=hash_pin(CORRECT_PIN),
            )
        )
    yield
    supplier_cache.clear()
    with session_scope() as db:
        db.query(Supplier).filter(Supplier.tenant_id == TENANT_ID).delete()
        tenant = db.get(Tenant, TENANT_ID)
        if tenant:
            db.delete(tenant)


async def _fresh_identified_session() -> CallSession:
    """A brand-new session, as a new call/`/agent/run` request would create."""
    session = CallSession(call_id=f"lockout-call-{id(object())}", tenant_id=TENANT_ID)
    found = await lookup_supplier(session, phone="+919200000001")
    assert found["found"] is True
    return session


def test_failed_attempts_persist_across_brand_new_sessions(lockout_supplier: None) -> None:
    """Each fresh session starts with zero session-local attempts, but the
    persistent counter on the Supplier row must still accumulate."""

    async def _one_wrong_guess_in_a_fresh_session() -> dict:
        session = await _fresh_identified_session()
        return await verify_pin(session, pin=WRONG_PIN)

    for _ in range(PERSISTENT_MAX_FAILED_PIN_ATTEMPTS - 1):
        result = asyncio.run(_one_wrong_guess_in_a_fresh_session())
        assert result["verified"] is False
        assert result["reason"] == "invalid_pin"

    with session_scope() as db:
        supplier = db.get(Supplier, SUPPLIER_ID)
        assert supplier.pin_failed_attempts == PERSISTENT_MAX_FAILED_PIN_ATTEMPTS - 1
        assert supplier.pin_locked_until is None


def test_persistent_lockout_engages_and_rejects_even_the_correct_pin(lockout_supplier: None) -> None:
    async def _one_wrong_guess_in_a_fresh_session() -> dict:
        session = await _fresh_identified_session()
        return await verify_pin(session, pin=WRONG_PIN)

    for _ in range(PERSISTENT_MAX_FAILED_PIN_ATTEMPTS):
        asyncio.run(_one_wrong_guess_in_a_fresh_session())

    with session_scope() as db:
        supplier = db.get(Supplier, SUPPLIER_ID)
        assert supplier.pin_failed_attempts >= PERSISTENT_MAX_FAILED_PIN_ATTEMPTS
        assert supplier.pin_locked_until is not None
        # SQLite returns naive datetimes even for timezone-aware columns.
        locked_until = supplier.pin_locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        assert locked_until > datetime.now(timezone.utc)

    async def _try_correct_pin_in_a_fresh_session() -> dict:
        session = await _fresh_identified_session()
        return await verify_pin(session, pin=CORRECT_PIN)

    locked_attempt = asyncio.run(_try_correct_pin_in_a_fresh_session())
    assert locked_attempt["verified"] is False
    assert locked_attempt["reason"] == "too_many_attempts"
    assert locked_attempt["locked"] is True


def test_lockout_expires_after_its_window(lockout_supplier: None) -> None:
    with session_scope() as db:
        supplier = db.get(Supplier, SUPPLIER_ID)
        supplier.pin_failed_attempts = PERSISTENT_MAX_FAILED_PIN_ATTEMPTS
        supplier.pin_locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)

    async def _try_correct_pin() -> dict:
        session = await _fresh_identified_session()
        return await verify_pin(session, pin=CORRECT_PIN)

    result = asyncio.run(_try_correct_pin())
    assert result["verified"] is True

    with session_scope() as db:
        supplier = db.get(Supplier, SUPPLIER_ID)
        assert supplier.pin_failed_attempts == 0
        assert supplier.pin_locked_until is None


def test_successful_verification_resets_the_persistent_counter(lockout_supplier: None) -> None:
    async def _one_wrong_guess_in_a_fresh_session() -> dict:
        session = await _fresh_identified_session()
        return await verify_pin(session, pin=WRONG_PIN)

    for _ in range(3):
        asyncio.run(_one_wrong_guess_in_a_fresh_session())

    with session_scope() as db:
        supplier = db.get(Supplier, SUPPLIER_ID)
        assert supplier.pin_failed_attempts == 3

    async def _correct_guess_in_a_fresh_session() -> dict:
        session = await _fresh_identified_session()
        return await verify_pin(session, pin=CORRECT_PIN)

    result = asyncio.run(_correct_guess_in_a_fresh_session())
    assert result["verified"] is True

    with session_scope() as db:
        supplier = db.get(Supplier, SUPPLIER_ID)
        assert supplier.pin_failed_attempts == 0
        assert supplier.pin_locked_until is None


IDENTITIES = {
    "lockout-owner-token": AuthUser(user_id="lockout-owner", email="owner@pin-lockout.test"),
}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_owner_pin_reset_clears_an_active_lockout(lockout_supplier: None, monkeypatch) -> None:
    monkeypatch.setenv("TENANT_AUTHORIZATION_ENFORCED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(auth, "_verify_token", lambda token: IDENTITIES.get(token))
    with session_scope() as db:
        db.add(
            TenantMember(
                id="tm-lockout-owner",
                tenant_id=TENANT_ID,
                user_id="lockout-owner",
                subject_email_hash=normalized_email_hash("owner@pin-lockout.test", fallback_subject="lockout-owner"),
                role="owner",
                status="active",
                invited_by="test",
                activated_at=datetime.now(timezone.utc),
            )
        )
        supplier = db.get(Supplier, SUPPLIER_ID)
        supplier.pin_failed_attempts = PERSISTENT_MAX_FAILED_PIN_ATTEMPTS
        supplier.pin_locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

    try:
        with TestClient(create_app()) as client:
            response = client.put(
                f"/api/tenants/{TENANT_ID}/caller-verification/{SUPPLIER_ID}/pin",
                headers=_headers("lockout-owner-token"),
                json={"pin": "1357", "confirm_pin": "1357"},
            )
            assert response.status_code == 200
    finally:
        get_settings.cache_clear()

    with session_scope() as db:
        supplier = db.get(Supplier, SUPPLIER_ID)
        assert supplier.pin_failed_attempts == 0
        assert supplier.pin_locked_until is None
        assert verify_pin_hash("1357", supplier.auth_pin_hash)
