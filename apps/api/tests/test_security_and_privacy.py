"""Tests for Day 52: UK GDPR Data Subject Rights, Retention Purge & Privacy APIs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import pytest
from fastapi.testclient import TestClient

from voxflow_api.auth import (
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    AuthUser,
    normalized_email_hash,
)
import voxflow_api.auth as auth_mod
from voxflow_api.config import get_settings
from voxflow_api.db import (
    Call,
    CommunicationLog,
    SessionLocal,
    Supplier,
    Tenant,
    TenantMember,
    session_scope,
)
from voxflow_api.main import app
from voxflow_api.services.privacy_service import (
    erase_data_subject,
    export_data_subject,
    mask_email_address,
    mask_phone_number,
)
from voxflow_api.services.retention_service import run_retention_purge

client = TestClient(app)

USER_OWNER = "usr-privacy-owner"
USER_OPERATOR = "usr-privacy-operator"
USER_VIEWER = "usr-privacy-viewer"

AUTH_USERS = {
    USER_OWNER: AuthUser(user_id=USER_OWNER, email="owner@privacy.test"),
    USER_OPERATOR: AuthUser(user_id=USER_OPERATOR, email="operator@privacy.test"),
    USER_VIEWER: AuthUser(user_id=USER_VIEWER, email="viewer@privacy.test"),
}


def _seed_tenant(tenant_id: str, name: str = "UK Tenant") -> None:
    with session_scope() as db:
        t = db.get(Tenant, tenant_id)
        if not t:
            t = Tenant(
                id=tenant_id,
                name=name,
                plan="growth",
                call_retention_days=90,
                transcript_retention_days=30,
                pii_masking_enabled=1,
                data_residency_region="eu-west-2",
            )
            db.add(t)
            db.flush()

        # Seed members for RBAC testing
        for uid, role in [(USER_OWNER, ROLE_OWNER), (USER_OPERATOR, ROLE_OPERATOR), (USER_VIEWER, ROLE_VIEWER)]:
            existing = (
                db.query(TenantMember)
                .filter(TenantMember.tenant_id == tenant_id, TenantMember.user_id == uid)
                .first()
            )
            if not existing:
                db.add(
                    TenantMember(
                        id=f"{tenant_id}_{uid}",
                        tenant_id=tenant_id,
                        user_id=uid,
                        subject_email_hash=normalized_email_hash(AUTH_USERS[uid].email),
                        role=role,
                        status="active",
                    )
                )


def test_phone_and_email_masking_helpers():
    """Verify phone and email masking algorithms."""
    assert mask_phone_number("+44 7911 123456") == "+44 7911 *** 456"
    assert mask_phone_number("+919876543210") == "+919876 *** 210"
    assert mask_phone_number("123") == "***"
    assert mask_phone_number("") == ""

    assert mask_email_address("john.doe@acme.co.uk") == "j***e@acme.co.uk"
    assert mask_email_address("ab@domain.com") == "a***@domain.com"
    assert mask_email_address("notanemail") == "notanemail"
    assert mask_email_address("") == ""


def test_dsar_export_tenant_scoped():
    """Verify GDPR DSAR export bundles all subject records and enforces tenant isolation."""
    tenant_a = "t_gdpr_export_a"
    tenant_b = "t_gdpr_export_b"
    _seed_tenant(tenant_a, "Tenant A")
    _seed_tenant(tenant_b, "Tenant B")

    subject_phone = "+447911000111"

    with session_scope() as db:
        # Tenant A records
        c1 = Call(
            id="call_gdpr_a1",
            tenant_id=tenant_a,
            caller_phone=subject_phone,
            caller_name="Alice Smith",
            transcript_json=json.dumps([{"role": "user", "text": "Where is my order?"}]),
            reason="Order tracking",
            outcome="Informed customer",
        )
        s1 = Supplier(
            id="sup_gdpr_a1",
            tenant_id=tenant_a,
            name="Alice Supplies Ltd",
            phone=subject_phone,
            city="London",
            state="Greater London",
            pincode="EC1A 1BB",
            contact_person="Alice Smith",
        )
        comm1 = CommunicationLog(
            id="comm_gdpr_a1",
            tenant_id=tenant_a,
            channel="email",
            recipient=subject_phone,
            subject="Order Dispatch Update",
            body="Your order is on the way.",
        )

        # Tenant B records with same subject phone
        c2 = Call(
            id="call_gdpr_b1",
            tenant_id=tenant_b,
            caller_phone=subject_phone,
            caller_name="Alice Smith B",
            transcript_json=json.dumps([{"role": "user", "text": "Tenant B call"}]),
        )

        db.add_all([c1, s1, comm1, c2])

    with session_scope() as db:
        export_a = export_data_subject(db, tenant_a, subject_phone)
        assert export_a["tenant_id"] == tenant_a
        assert export_a["subject"] == subject_phone
        assert export_a["counts"]["calls"] == 1
        assert export_a["counts"]["suppliers"] == 1
        assert export_a["counts"]["communication_logs"] == 1
        assert export_a["records"]["calls"][0]["id"] == "call_gdpr_a1"
        assert export_a["records"]["suppliers"][0]["id"] == "sup_gdpr_a1"

        # Tenant A export must NOT contain Tenant B call
        call_ids = [c["id"] for c in export_a["records"]["calls"]]
        assert "call_gdpr_b1" not in call_ids


def test_right_to_erasure_anonymization():
    """Verify right to erasure anonymizes caller records and wipes transcripts."""
    tenant_id = "t_gdpr_erase"
    _seed_tenant(tenant_id, "Erase Tenant")
    subject_phone = "+447911999888"

    with session_scope() as db:
        call = Call(
            id="call_erase_test_1",
            tenant_id=tenant_id,
            caller_phone=subject_phone,
            caller_name="Bob Jones",
            transcript_json=json.dumps([{"role": "user", "text": "Personal data here"}]),
            reason="Complaint",
            solution="Handled",
            staff_resolution="Resolved by staff",
        )
        db.add(call)

    with session_scope() as db:
        result = erase_data_subject(
            db=db,
            tenant_id=tenant_id,
            search_phone_or_email=subject_phone,
            erased_by_user_id="owner_user_1",
        )
        assert result["anonymized_calls"] == 1

    with session_scope() as db:
        c_refreshed = db.get(Call, "call_erase_test_1")
        assert c_refreshed is not None
        assert "999" not in c_refreshed.caller_phone or c_refreshed.caller_phone.startswith("+447911 ***")
        assert c_refreshed.caller_name == "REDACTED"
        assert c_refreshed.transcript_json == "[]"
        assert c_refreshed.reason == ""
        assert c_refreshed.solution == ""
        assert c_refreshed.staff_resolution == ""


def test_retention_purge_and_dry_run():
    """Verify retention purge scrubs expired transcripts and anonymizes old calls."""
    tenant_id = "t_gdpr_retention_purge"
    _seed_tenant(tenant_id, "Purge Tenant")

    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=45)
    ancient_date = now - timedelta(days=120)
    fresh_date = now - timedelta(days=5)

    with session_scope() as db:
        t = db.get(Tenant, tenant_id)
        assert t is not None
        t.transcript_retention_days = 30
        t.call_retention_days = 90

        # Call 1: 45 days old -> transcript should be purged (since > 30d), call record retained (since <= 90d)
        c_old = Call(
            id="call_purge_45d",
            tenant_id=tenant_id,
            caller_phone="+447911111111",
            caller_name="Old Caller",
            transcript_json=json.dumps([{"role": "user", "text": "Old transcript"}]),
            started_at=old_date,
        )
        # Call 2: 120 days old -> both call record & transcript should be anonymized (since > 90d)
        c_ancient = Call(
            id="call_purge_120d",
            tenant_id=tenant_id,
            caller_phone="+447911222222",
            caller_name="Ancient Caller",
            transcript_json=json.dumps([{"role": "user", "text": "Ancient transcript"}]),
            started_at=ancient_date,
        )
        # Call 3: 5 days old -> fresh, untouched
        c_fresh = Call(
            id="call_purge_5d",
            tenant_id=tenant_id,
            caller_phone="+447911333333",
            caller_name="Fresh Caller",
            transcript_json=json.dumps([{"role": "user", "text": "Fresh transcript"}]),
            started_at=fresh_date,
        )
        db.add_all([c_old, c_ancient, c_fresh])

    # 1. Dry Run Test
    with session_scope() as db:
        dry_res = run_retention_purge(db, tenant_id=tenant_id, dry_run=True)
        assert dry_res["dry_run"] is True
        assert dry_res["transcripts_purged"] >= 2
        assert dry_res["calls_anonymized"] >= 1

    with session_scope() as db:
        c1 = db.get(Call, "call_purge_45d")
        assert c1.transcript_json != "[]"

    # 2. Live Purge Execution
    with session_scope() as db:
        live_res = run_retention_purge(db, tenant_id=tenant_id, dry_run=False, triggered_by_user_id="admin_1")
        assert live_res["dry_run"] is False
        assert live_res["transcripts_purged"] >= 2
        assert live_res["calls_anonymized"] >= 1

    with session_scope() as db:
        c_old_r = db.get(Call, "call_purge_45d")
        c_ancient_r = db.get(Call, "call_purge_120d")
        c_fresh_r = db.get(Call, "call_purge_5d")

        assert c_old_r.transcript_json == "[]"
        assert c_ancient_r.caller_name == "REDACTED"
        assert c_ancient_r.caller_phone == "REDACTED"
        assert c_fresh_r.transcript_json != "[]"
        assert c_fresh_r.caller_name == "Fresh Caller"


def test_privacy_api_endpoints_and_rbac(monkeypatch):
    """Verify REST endpoints under /api/tenants/{tenant_id}/privacy with RBAC matrix."""
    settings = get_settings()
    monkeypatch.setattr(settings, "tenant_authorization_enforced", True)
    monkeypatch.setattr(settings, "demo_mode_enabled", False)
    monkeypatch.setattr(auth_mod, "_verify_token", lambda token: AUTH_USERS.get(token))

    tenant_id = "t_gdpr_api"
    _seed_tenant(tenant_id, "API Test Tenant")

    headers_viewer = {"Authorization": f"Bearer {USER_VIEWER}"}
    headers_operator = {"Authorization": f"Bearer {USER_OPERATOR}"}
    headers_owner = {"Authorization": f"Bearer {USER_OWNER}"}

    # 1. GET retention (Read access: Owner, Operator, Viewer)
    resp = client.get(f"/api/tenants/{tenant_id}/privacy/retention", headers=headers_viewer)
    assert resp.status_code == 200
    data = resp.json()
    assert "retention" in data
    assert data["retention"]["call_retention_days"] == 90
    assert data["retention"]["transcript_retention_days"] == 30

    # 2. PATCH retention (Owner only; Viewer & Operator should get 403)
    resp_viewer_patch = client.patch(
        f"/api/tenants/{tenant_id}/privacy/retention",
        json={"transcript_retention_days": 14, "call_retention_days": 60},
        headers=headers_viewer,
    )
    assert resp_viewer_patch.status_code == 403

    resp_owner_patch = client.patch(
        f"/api/tenants/{tenant_id}/privacy/retention",
        json={"transcript_retention_days": 14, "call_retention_days": 60},
        headers=headers_owner,
    )
    assert resp_owner_patch.status_code == 200
    assert resp_owner_patch.json()["retention"]["transcript_retention_days"] == 14
    assert resp_owner_patch.json()["retention"]["call_retention_days"] == 60

    # 3. POST export (Owner or Operator allowed; Viewer should get 403)
    resp_export_viewer = client.post(
        f"/api/tenants/{tenant_id}/privacy/export",
        json={"search_phone_or_email": "+447911123456"},
        headers=headers_viewer,
    )
    assert resp_export_viewer.status_code == 403

    resp_export = client.post(
        f"/api/tenants/{tenant_id}/privacy/export",
        json={"search_phone_or_email": "+447911123456"},
        headers=headers_operator,
    )
    assert resp_export.status_code == 200
    assert resp_export.json()["ok"] is True
    assert "export" in resp_export.json()

    # 4. POST erase (Requires confirmation token 'DELETE DATA' & ROLE_OWNER)
    resp_erase_bad_token = client.post(
        f"/api/tenants/{tenant_id}/privacy/erase",
        json={"search_phone_or_email": "+447911123456", "confirmation_token": "wrong"},
        headers=headers_owner,
    )
    assert resp_erase_bad_token.status_code == 400

    resp_erase_operator = client.post(
        f"/api/tenants/{tenant_id}/privacy/erase",
        json={"search_phone_or_email": "+447911123456", "confirmation_token": "DELETE DATA"},
        headers=headers_operator,
    )
    assert resp_erase_operator.status_code == 403

    resp_erase_owner = client.post(
        f"/api/tenants/{tenant_id}/privacy/erase",
        json={"search_phone_or_email": "+447911123456", "confirmation_token": "DELETE DATA"},
        headers=headers_owner,
    )
    assert resp_erase_owner.status_code == 200
    assert resp_erase_owner.json()["ok"] is True

    # 5. POST purge (Dry run & Live, Owner only)
    resp_purge_viewer = client.post(
        f"/api/tenants/{tenant_id}/privacy/purge?dry_run=true",
        headers=headers_viewer,
    )
    assert resp_purge_viewer.status_code == 403

    resp_purge = client.post(
        f"/api/tenants/{tenant_id}/privacy/purge?dry_run=true",
        headers=headers_owner,
    )
    assert resp_purge.status_code == 200
    assert resp_purge.json()["purge"]["dry_run"] is True

    # 6. GET purge logs
    resp_logs = client.get(
        f"/api/tenants/{tenant_id}/privacy/purge-logs",
        headers=headers_viewer,
    )
    assert resp_logs.status_code == 200
    assert isinstance(resp_logs.json()["logs"], list)
