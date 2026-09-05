"""Superadmin visibility tests (Phase 0 step 5).

The production authorization gate is enabled explicitly here. Token
verification is replaced with deterministic in-process identities — no
Supabase request is made. Access reads: env allow-list
(``PLATFORM_ADMIN_USER_IDS``) OR an ``is_superadmin`` membership row that is
still ``active``. Everything else gets 403.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from voxflow_api import auth
from voxflow_api.auth import AuthUser, normalized_email_hash
from voxflow_api.config import get_settings
from voxflow_api.db import TenantMember, reset_db, session_scope
from voxflow_api.main import create_app
from voxflow_api.seed import seed


IDENTITIES = {
    "env-admin-token": AuthUser(user_id="env-admin", email="env-admin@example.test"),
    "flag-admin-token": AuthUser(user_id="flag-admin", email="flag-admin@example.test"),
    "revoked-flag-token": AuthUser(user_id="revoked-flag", email="revoked@example.test"),
    "outsider-token": AuthUser(user_id="outsider-subject", email="outsider@example.test"),
}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _flag_row(member_id: str, user_id: str, email: str, *, status: str = "active") -> TenantMember:
    return TenantMember(
        id=member_id,
        tenant_id="varun",
        user_id=user_id,
        subject_email_hash=normalized_email_hash(email, fallback_subject=user_id),
        role="viewer",
        status=status,
        invited_by="env-admin",
        is_superadmin=True,
        activated_at=datetime.now(timezone.utc) if status == "active" else None,
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TENANT_AUTHORIZATION_ENFORCED", "true")
    monkeypatch.setenv("PLATFORM_ADMIN_USER_IDS", "env-admin")
    get_settings.cache_clear()
    monkeypatch.setattr(auth, "_verify_token", lambda token: IDENTITIES.get(token))
    reset_db()
    seed(reset=True)
    with session_scope() as db:
        db.add_all(
            [
                _flag_row("tm-flag-admin", "flag-admin", "flag-admin@example.test"),
                _flag_row("tm-revoked-flag", "revoked-flag", "revoked@example.test", status="revoked"),
            ]
        )
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_env_allow_list_admin_lists_tenants_and_minutes(client):
    r = client.get("/api/superadmin/tenants", headers=_headers("env-admin-token"))
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_count"] >= 1
    assert any(t["tenant_id"] == "varun" for t in body["tenants"])
    for row in body["tenants"]:
        assert set(row) == {
            "tenant_id", "name", "active", "plan", "call_count", "minutes_used",
            "subscription_status", "failed_payment_count", "current_period_end",
        }
        assert row["call_count"] >= 0
        assert row["minutes_used"] >= 0
    # Seeded varun fixtures carry real call history, so at least one tenant
    # shows usage — an all-zero listing would mean the minutes aggregation
    # silently read nothing.
    assert body["total_calls"] >= 1
    assert body["total_minutes"] >= 1
    assert body["total_calls"] == sum(t["call_count"] for t in body["tenants"])
    assert body["total_minutes"] == sum(t["minutes_used"] for t in body["tenants"])


def test_flagged_membership_row_confirms_superadmin_without_env_entry(client):
    r = client.get("/api/superadmin/tenants", headers=_headers("flag-admin-token"))
    assert r.status_code == 200
    assert r.json()["tenant_count"] >= 1


def test_revoked_flag_row_is_denied(client):
    r = client.get("/api/superadmin/tenants", headers=_headers("revoked-flag-token"))
    assert r.status_code == 403
    assert r.json()["detail"] == "superadmin_required"


def test_outsider_is_denied(client):
    r = client.get("/api/superadmin/tenants", headers=_headers("outsider-token"))
    assert r.status_code == 403
    assert r.json()["detail"] == "superadmin_required"


def test_anonymous_is_denied(client):
    r = client.get("/api/superadmin/tenants")
    assert r.status_code in (401, 403)
