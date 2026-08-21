"""Tenant membership lifecycle and server-side authorization tests.

The production-default tenant authorization gate is enabled explicitly here.
Token verification is replaced with deterministic in-process identities; no
Supabase request, email delivery, worker, provider, callback, or outbound call
is made.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient

from voxflow_api import auth
from voxflow_api.auth import AuthUser, normalized_email_hash
from voxflow_api.config import get_settings
from voxflow_api.db import TenantMember, reset_db, session_scope
from voxflow_api.main import create_app
from voxflow_api.seed import seed


IDENTITIES = {
    "owner-token": AuthUser(user_id="owner-subject", email="owner@example.test"),
    "operator-token": AuthUser(user_id="operator-subject", email="operator@example.test"),
    "viewer-token": AuthUser(user_id="viewer-subject", email="viewer@example.test"),
    "recipient-token": AuthUser(user_id="recipient-subject", email="recipient@example.test"),
    "outsider-token": AuthUser(user_id="outsider-subject", email="outsider@example.test"),
    "platform-token": AuthUser(user_id="platform-admin", email="platform@example.test"),
}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _member(member_id: str, user_id: str | None, email: str, role: str, status: str = "active") -> TenantMember:
    return TenantMember(
        id=member_id,
        tenant_id="varun",
        user_id=user_id,
        subject_email_hash=normalized_email_hash(email, fallback_subject=user_id or ""),
        role=role,
        status=status,
        invited_by="owner-subject",
        activated_at=datetime.now(timezone.utc) if status == "active" else None,
    )


@pytest.fixture
def secured_client(monkeypatch):
    monkeypatch.setenv("TENANT_AUTHORIZATION_ENFORCED", "true")
    monkeypatch.setenv("PLATFORM_ADMIN_USER_IDS", "platform-admin")
    monkeypatch.setenv("DURABLE_CAMPAIGN_WORKER_ENABLED", "false")
    monkeypatch.setenv("DURABLE_CAMPAIGN_DRY_RUN", "true")
    monkeypatch.setenv("DURABLE_SIDE_EFFECTS_WORKER_ENABLED", "false")
    monkeypatch.setenv("DURABLE_SIDE_EFFECTS_DRY_RUN", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(auth, "_verify_token", lambda token: IDENTITIES.get(token))
    reset_db()
    seed(reset=True)
    with session_scope() as db:
        db.add_all(
            [
                _member("tm-owner", "owner-subject", "owner@example.test", "owner"),
                _member("tm-operator", "operator-subject", "operator@example.test", "operator"),
                _member("tm-viewer", "viewer-subject", "viewer@example.test", "viewer"),
            ]
        )
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


def test_membership_discovery_requires_identity_and_returns_only_active_authorized_tenants(secured_client):
    anonymous = secured_client.get("/api/tenants/memberships")
    owner = secured_client.get("/api/tenants/memberships", headers=_headers("owner-token"))
    outsider = secured_client.get("/api/tenants/memberships", headers=_headers("outsider-token"))
    assert anonymous.status_code == 401
    assert owner.status_code == 200
    assert owner.json()["demo_mode"] is False
    assert [row["tenant_id"] for row in owner.json()["memberships"]] == ["varun"]
    assert outsider.status_code == 200
    assert outsider.json()["memberships"] == []


def test_owner_invite_persists_only_hashed_identity_and_recipient_accepts(secured_client):
    invitation = secured_client.post(
        "/api/tenants/varun/members/invite",
        headers=_headers("owner-token"),
        json={"email": "recipient@example.test", "role": "operator"},
    )
    assert invitation.status_code == 200
    payload = invitation.json()
    assert payload["created"] is True
    assert payload["delivery"] == "manual_design_partner_invitation_required"
    assert "recipient@example.test" not in str(payload)
    assert payload["membership"]["status"] == "invited"

    with session_scope() as db:
        row = db.query(TenantMember).filter(TenantMember.id == payload["membership"]["id"]).first()
        assert row is not None
        assert row.subject_email_hash == sha256(b"recipient@example.test").hexdigest()
        assert row.user_id is None

    accepted = secured_client.post(
        "/api/tenants/memberships/accept",
        headers=_headers("recipient-token"),
        json={"tenant_id": "varun"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["created"] is True
    assert accepted.json()["membership"]["status"] == "active"
    assert accepted.json()["membership"]["user_id"] == "recipient-subject"


def test_roles_enforce_operator_visibility_owner_only_invites_and_revoke_protection(secured_client):
    operator_list = secured_client.get("/api/tenants/varun/members", headers=_headers("operator-token"))
    viewer_list = secured_client.get("/api/tenants/varun/members", headers=_headers("viewer-token"))
    operator_invite = secured_client.post(
        "/api/tenants/varun/members/invite",
        headers=_headers("operator-token"),
        json={"email": "new@example.test", "role": "viewer"},
    )
    self_revoke = secured_client.delete("/api/tenants/varun/members/owner-subject", headers=_headers("owner-token"))
    assert operator_list.status_code == 200
    assert viewer_list.status_code == 403
    assert operator_invite.status_code == 403
    assert self_revoke.status_code == 409
    assert self_revoke.json()["detail"] == "owner_cannot_revoke_self"


def test_owner_can_revoke_other_active_member_but_not_the_last_active_owner(secured_client):
    revoke_operator = secured_client.delete(
        "/api/tenants/varun/members/operator-subject",
        headers=_headers("owner-token"),
    )
    assert revoke_operator.status_code == 200
    assert revoke_operator.json()["membership"]["status"] == "revoked"
    with session_scope() as db:
        db.add(_member("tm-owner-two", "owner-two-subject", "owner.two@example.test", "owner"))
    revoke_second_owner = secured_client.delete(
        "/api/tenants/varun/members/owner-two-subject",
        headers=_headers("owner-token"),
    )
    assert revoke_second_owner.status_code == 200


def test_data_routes_use_active_membership_not_query_tenant_or_jwt_metadata(secured_client):
    authorized = secured_client.get("/api/summary?tenant_id=varun", headers=_headers("viewer-token"))
    cross_tenant = secured_client.get("/api/summary?tenant_id=amul", headers=_headers("viewer-token"))
    demo_read = secured_client.get(
        "/api/summary?tenant_id=varun",
        headers={"X-VoxFlow-Demo": "enabled", "X-VoxFlow-Demo-Tenant": "varun"},
    )
    demo_write = secured_client.post(
        "/api/orders?tenant_id=varun",
        headers={"X-VoxFlow-Demo": "enabled", "X-VoxFlow-Demo-Tenant": "varun"},
        json={"supplier_id": "sup-varun-001", "items": [{"sku": "VAR-CARTON-100", "quantity": 1}]},
    )
    assert authorized.status_code == 200
    assert cross_tenant.status_code == 403
    assert demo_read.status_code == 200
    assert demo_write.status_code == 403


def test_admin_and_workspace_provisioning_require_platform_admin_and_bootstrap_owner_membership(secured_client):
    non_admin = secured_client.post(
        "/api/workspaces/provision",
        headers=_headers("owner-token"),
        json={"tenant_id": "acme", "name": "Acme", "seed_starter_data": False},
    )
    admin = secured_client.post(
        "/api/workspaces/provision",
        headers=_headers("platform-token"),
        json={"tenant_id": "acme", "name": "Acme", "seed_starter_data": False},
    )
    assert non_admin.status_code == 403
    assert admin.status_code == 200
    assert admin.json()["message"].endswith("outbound operation was activated.")
    with session_scope() as db:
        owner = db.query(TenantMember).filter(TenantMember.tenant_id == "acme").first()
        assert owner is not None
        assert owner.user_id == "platform-admin"
        assert owner.role == "owner"


def test_legacy_direct_outbound_endpoint_is_server_blocked_before_provider_use(secured_client):
    response = secured_client.post(
        "/api/calls/outbound?tenant_id=varun",
        headers=_headers("owner-token"),
        json={"to_phone": "+919876543210", "instruction": "test", "language": "en"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "outbound_calls_disabled_by_safety_posture"


def test_simulator_websocket_is_limited_to_the_fixed_demo_tenant(secured_client):
    with secured_client.websocket_connect("/ws/call") as websocket:
        websocket.send_json({"type": "start", "tenant_id": "amul", "language": "en"})
        denied = websocket.receive_json()
        assert denied == {"type": "error", "message": "simulator_tenant_authorization_required"}

        websocket.send_json({"type": "start", "tenant_id": "varun", "language": "en"})
        ready = websocket.receive_json()
        assert ready["type"] == "ready"
        websocket.send_json({"type": "end"})
        assert websocket.receive_json()["type"] == "ended"
