"""Comprehensive Role-Based Access Control (RBAC) Matrix Test Suite.

Validates the 3-tier authorization model:
- Owner: Full administrative & operational privileges, protected last-owner invariant.
- Operator (Staff): Operational data CRUD, escalations, imports; blocked from settings & users.
- Viewer: Read-only access across domain entities & telemetry; all mutations blocked (403).
"""

from __future__ import annotations

from datetime import datetime, timezone
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
    Appointment,
    Call,
    CommunicationLog,
    Order,
    OutboundCampaign,
    Product,
    Shipment,
    Stock,
    Supplier,
    Tenant,
    TenantMember,
    TenantPhoneNumber,
    session_scope,
)
from voxflow_api.main import create_app


TEST_TENANT = "rbac-tenant"

USER_OWNER = "usr-rbac-owner"
USER_OPERATOR = "usr-rbac-operator"
USER_VIEWER = "usr-rbac-viewer"

AUTH_USERS = {
    USER_OWNER: AuthUser(user_id=USER_OWNER, email="owner@rbac.com"),
    USER_OPERATOR: AuthUser(user_id=USER_OPERATOR, email="operator@rbac.com"),
    USER_VIEWER: AuthUser(user_id=USER_VIEWER, email="viewer@rbac.com"),
}


@pytest.fixture
def rbac_client(monkeypatch):
    """Set up a test environment with tenant authorization enforced and seed 3 roles."""
    settings = get_settings()
    monkeypatch.setattr(settings, "tenant_authorization_enforced", True)
    monkeypatch.setattr(settings, "demo_mode_enabled", False)
    monkeypatch.setattr(auth_mod, "_verify_token", lambda token: AUTH_USERS.get(token))

    now = datetime.now(timezone.utc)

    with session_scope() as db:
        # Clean previous test state
        db.query(Appointment).filter(Appointment.tenant_id == TEST_TENANT).delete()
        db.query(CommunicationLog).filter(CommunicationLog.tenant_id == TEST_TENANT).delete()
        db.query(Call).filter(Call.tenant_id == TEST_TENANT).delete()
        db.query(Shipment).filter(Shipment.tenant_id == TEST_TENANT).delete()
        db.query(Order).filter(Order.tenant_id == TEST_TENANT).delete()
        db.query(Stock).filter(Stock.tenant_id == TEST_TENANT).delete()
        db.query(Product).filter(Product.tenant_id == TEST_TENANT).delete()
        db.query(Supplier).filter(Supplier.tenant_id == TEST_TENANT).delete()
        db.query(TenantPhoneNumber).filter(TenantPhoneNumber.tenant_id == TEST_TENANT).delete()
        db.query(OutboundCampaign).filter(OutboundCampaign.tenant_id == TEST_TENANT).delete()
        db.query(TenantMember).filter(TenantMember.tenant_id == TEST_TENANT).delete()
        db.query(Tenant).filter(Tenant.id == TEST_TENANT).delete()

        # Create Tenant
        tenant = Tenant(
            id=TEST_TENANT,
            name="RBAC Validation Depot",
            agent_name="RbacAgent",
            default_language="en",
            plan="growth",
            voice_persona="professional",
            active=1,
            created_at=now,
        )
        db.add(tenant)
        db.flush()

        # Seed 3 distinct members
        members = [
            TenantMember(
                id="tm-rbac-owner",
                tenant_id=TEST_TENANT,
                user_id=USER_OWNER,
                subject_email_hash=normalized_email_hash("owner@rbac.com"),
                role=ROLE_OWNER,
                status="active",
                activated_at=now,
            ),
            TenantMember(
                id="tm-rbac-operator",
                tenant_id=TEST_TENANT,
                user_id=USER_OPERATOR,
                subject_email_hash=normalized_email_hash("operator@rbac.com"),
                role=ROLE_OPERATOR,
                status="active",
                activated_at=now,
            ),
            TenantMember(
                id="tm-rbac-viewer",
                tenant_id=TEST_TENANT,
                user_id=USER_VIEWER,
                subject_email_hash=normalized_email_hash("viewer@rbac.com"),
                role=ROLE_VIEWER,
                status="active",
                activated_at=now,
            ),
        ]
        db.add_all(members)
        db.flush()

        # Seed sample entities
        sup = Supplier(
            id="sup-rbac-1",
            tenant_id=TEST_TENANT,
            name="RBAC Premier Logistics",
            phone="+441632960300",
            city="London",
            state="Greater London",
            pincode="EC1A 1BB",
            contact_person="Sam RBAC",
            gstin="GB555666777",
            active=1,
        )
        prod = Product(
            sku="SKU-RBAC-01",
            tenant_id=TEST_TENANT,
            name="Industrial Valve",
            category="hardware",
            pack_size="1 unit",
            mrp_inr=800.0,
        )
        stock = Stock(
            sku="SKU-RBAC-01",
            tenant_id=TEST_TENANT,
            warehouse="Main-Depot",
            quantity=150,
        )
        order = Order(
            id="PO-RBAC-100",
            tenant_id=TEST_TENANT,
            supplier_id="sup-rbac-1",
            status="pending",
            items_json=json.dumps([{"sku": "SKU-RBAC-01", "quantity": 25}]),
            total_qty=25,
        )
        call = Call(
            id="call-rbac-1",
            tenant_id=TEST_TENANT,
            caller_phone="+441632960300",
            caller_name="Sam RBAC",
            intent="order_status",
            outcome="completed",
            started_at=now,
            ended_at=now,
            duration_sec=40,
            escalated=1,
            escalation_priority="high",
            escalation_status="pending",
            resolution_status="escalated",
        )
        phone = TenantPhoneNumber(
            phone_number="+441632960333",
            tenant_id=TEST_TENANT,
            provider="connect",
            active=1,
            route_language="en",
            verification_mode="standard",
            created_at=now,
        )
        db.add_all([sup, prod, stock, order, call, phone])
        db.commit()

    app = create_app()
    return TestClient(app)


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}", "X-VoxFlow-User-Id": user_id}


# ==============================================================================
# 1. Viewer Role Tests (Read-Only Enforcement)
# ==============================================================================


def test_viewer_can_read_all_domain_resources(rbac_client: TestClient):
    """Assert Viewer role can read resources across all domain endpoints."""
    client = rbac_client
    headers = _auth(USER_VIEWER)

    read_endpoints = [
        f"/api/summary?tenant_id={TEST_TENANT}",
        f"/api/suppliers?tenant_id={TEST_TENANT}",
        f"/api/suppliers/sup-rbac-1?tenant_id={TEST_TENANT}",
        f"/api/stock?tenant_id={TEST_TENANT}",
        f"/api/orders?tenant_id={TEST_TENANT}",
        f"/api/orders/PO-RBAC-100?tenant_id={TEST_TENANT}",
        f"/api/shipments?tenant_id={TEST_TENANT}",
        f"/api/calls?tenant_id={TEST_TENANT}",
        f"/api/calls/call-rbac-1?tenant_id={TEST_TENANT}",
        f"/api/appointments?tenant_id={TEST_TENANT}",
        f"/api/communications?tenant_id={TEST_TENANT}",
        f"/api/analytics/overview?tenant_id={TEST_TENANT}",
        f"/api/jobs/health?tenant_id={TEST_TENANT}",
        f"/api/campaigns?tenant_id={TEST_TENANT}",
        f"/api/tenants/{TEST_TENANT}/escalations",
        f"/api/tenants/{TEST_TENANT}/escalations/metrics",
        f"/api/tenants/{TEST_TENANT}/escalations/call-rbac-1",
        f"/api/admin/tenants/{TEST_TENANT}/agent-settings",
        f"/api/admin/tenants/{TEST_TENANT}/phone-numbers",
        f"/api/admin/tenants/{TEST_TENANT}/caller-pins",
        f"/api/tenants/{TEST_TENANT}/evals/scorecard",
    ]

    for ep in read_endpoints:
        res = client.get(ep, headers=headers)
        assert res.status_code == 200, f"Viewer read failed on {ep}: {res.status_code} - {res.text}"


def test_viewer_is_strictly_blocked_from_all_mutations(rbac_client: TestClient):
    """Assert Viewer role is blocked with 403 Forbidden on all POST/PATCH/DELETE endpoints."""
    client = rbac_client
    headers = _auth(USER_VIEWER)

    # 1. Create Supplier
    res = client.post(
        f"/api/suppliers?tenant_id={TEST_TENANT}",
        json={"name": "New Sup", "phone": "+441632960400", "city": "Leeds", "state": "Yorkshire", "pincode": "LS1", "contact_person": "P", "gstin": "GB123"},
        headers=headers,
    )
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"

    # 2. Create Order
    res = client.post(
        f"/api/orders?tenant_id={TEST_TENANT}",
        json={"supplier_id": "sup-rbac-1", "items": [{"sku": "SKU-RBAC-01", "quantity": 5}]},
        headers=headers,
    )
    assert res.status_code == 403

    # 3. Create Appointment
    res = client.post(
        f"/api/appointments?tenant_id={TEST_TENANT}",
        json={"supplier_id": "sup-rbac-1", "datetime": "2026-09-02T14:00:00Z", "purpose": "Audit"},
        headers=headers,
    )
    assert res.status_code == 403

    # 4. Create Communication
    res = client.post(
        f"/api/communications?tenant_id={TEST_TENANT}",
        json={"channel": "email", "recipient": "sup@rbac.com", "subject": "Notice", "body": "Hello"},
        headers=headers,
    )
    assert res.status_code == 403

    # 5. Patch Call Resolution
    res = client.patch(
        f"/api/calls/call-rbac-1/resolution?tenant_id={TEST_TENANT}",
        json={"staff_resolution": "Viewer attempt"},
        headers=headers,
    )
    assert res.status_code == 403

    # 6. Bulk CSV Import
    res = client.post(
        f"/api/data/products/import?tenant_id={TEST_TENANT}",
        data={"csv_text": "sku,name,category,pack_size,mrp_inr\nSKU-1,X,gen,1,10.0\n", "mode": "upsert"},
        headers=headers,
    )
    assert res.status_code == 403

    # 7. Escalation Assignment & Resolution
    res_assign = client.patch(f"/api/tenants/{TEST_TENANT}/escalations/call-rbac-1/assign", json={"assigned_to_user_id": USER_VIEWER}, headers=headers)
    assert res_assign.status_code == 403
    res_resolve = client.patch(f"/api/tenants/{TEST_TENANT}/escalations/call-rbac-1/resolve", json={"status": "resolved", "staff_resolution": "Done"}, headers=headers)
    assert res_resolve.status_code == 403

    # 8. Member List & Management
    res_members = client.get(f"/api/tenants/{TEST_TENANT}/members", headers=headers)
    assert res_members.status_code == 403
    res_inv = client.post(f"/api/tenants/{TEST_TENANT}/members/invite", json={"email": "new@rbac.com", "role": "viewer"}, headers=headers)
    assert res_inv.status_code == 403
    res_role = client.patch(f"/api/tenants/{TEST_TENANT}/members/{USER_OPERATOR}/role", json={"role": "viewer"}, headers=headers)
    assert res_role.status_code == 403


# ==============================================================================
# 2. Operator (Staff) Role Tests
# ==============================================================================


def test_operator_can_perform_operational_actions(rbac_client: TestClient):
    """Assert Operator role can create suppliers, orders, appointments, and resolve escalations."""
    client = rbac_client
    headers = _auth(USER_OPERATOR)

    # 1. Create Supplier
    res_sup = client.post(
        f"/api/suppliers?tenant_id={TEST_TENANT}",
        json={"name": "Operator Created Supplier", "phone": "+441632960444", "city": "Bristol", "state": "Bristol", "pincode": "BS1", "contact_person": "Op Person", "gstin": "GB444555666"},
        headers=headers,
    )
    assert res_sup.status_code == 200

    # 2. Create Order
    res_ord = client.post(
        f"/api/orders?tenant_id={TEST_TENANT}",
        json={"supplier_id": "sup-rbac-1", "items": [{"sku": "SKU-RBAC-01", "quantity": 10}], "notes": "Operator PO"},
        headers=headers,
    )
    assert res_ord.status_code == 200

    # 3. Create Appointment
    res_app = client.post(
        f"/api/appointments?tenant_id={TEST_TENANT}",
        json={"supplier_id": "sup-rbac-1", "datetime": "2026-09-05T09:00:00Z", "purpose": "Operator Dock Slot"},
        headers=headers,
    )
    assert res_app.status_code == 200

    # 4. Create Communication
    res_comm = client.post(
        f"/api/communications?tenant_id={TEST_TENANT}",
        json={"channel": "sms", "recipient": "+441632960444", "subject": "Update", "body": "Order received"},
        headers=headers,
    )
    assert res_comm.status_code == 200

    # 5. Assign and Resolve Escalation
    res_assign = client.patch(
        f"/api/tenants/{TEST_TENANT}/escalations/call-rbac-1/assign",
        json={"assigned_to_user_id": USER_OPERATOR},
        headers=headers,
    )
    assert res_assign.status_code == 200
    res_resolve = client.patch(
        f"/api/tenants/{TEST_TENANT}/escalations/call-rbac-1/resolve",
        json={"status": "resolved", "resolution_category": "callback_completed", "staff_resolution": "Spoke to caller, resolved delivery."},
        headers=headers,
    )
    assert res_resolve.status_code == 200

    # 6. View Members List
    res_mem = client.get(f"/api/tenants/{TEST_TENANT}/members", headers=headers)
    assert res_mem.status_code == 200
    assert len(res_mem.json()["members"]) >= 3


def test_operator_blocked_from_administrative_and_user_management(rbac_client: TestClient):
    """Assert Operator role cannot mutate settings, DIDs, caller PINs, or team memberships."""
    client = rbac_client
    headers = _auth(USER_OPERATOR)

    # 1. Cannot update tenant settings / persona
    res_set = client.patch(
        f"/api/admin/tenants/{TEST_TENANT}/agent-settings",
        json={"voice_persona": "assertive", "business_hours_enabled": True},
        headers=headers,
    )
    assert res_set.status_code == 403

    # 2. Cannot configure phone numbers
    res_phone = client.post(
        f"/api/admin/tenants/{TEST_TENANT}/phone-numbers",
        json={"phone_number": "+441632960999", "route_language": "en"},
        headers=headers,
    )
    assert res_phone.status_code == 403

    # 3. Cannot set caller PIN
    res_pin = client.put(
        f"/api/admin/tenants/{TEST_TENANT}/suppliers/sup-rbac-1/caller-pin",
        json={"pin": "1234", "confirm_pin": "1234"},
        headers=headers,
    )
    assert res_pin.status_code == 403

    # 4. Cannot invite team members
    res_inv = client.post(
        f"/api/tenants/{TEST_TENANT}/members/invite",
        json={"email": "new_hire@rbac.com", "role": "viewer"},
        headers=headers,
    )
    assert res_inv.status_code == 403

    # 5. Cannot change member roles
    res_role = client.patch(
        f"/api/tenants/{TEST_TENANT}/members/{USER_VIEWER}/role",
        json={"role": "operator"},
        headers=headers,
    )
    assert res_role.status_code == 403

    # 6. Cannot revoke members
    res_rev = client.delete(
        f"/api/tenants/{TEST_TENANT}/members/{USER_VIEWER}",
        headers=headers,
    )
    assert res_rev.status_code == 403

    # 7. Cannot import CSV with auth_pin
    pin_csv = "name,phone,city,state,pincode,contact_person,gstin,auth_pin\nSecret Sup,+441632960777,London,UK,EC1,P,GB1,9999\n"
    res_csv_pin = client.post(
        f"/api/data/suppliers/import?tenant_id={TEST_TENANT}",
        data={"csv_text": pin_csv, "mode": "upsert"},
        headers=headers,
    )
    assert res_csv_pin.status_code == 403


# ==============================================================================
# 3. Owner Role & Last-Owner Invariant Protection Tests
# ==============================================================================


def test_owner_can_manage_settings_members_and_roles(rbac_client: TestClient):
    """Assert Owner role has full administrative authority."""
    client = rbac_client
    headers = _auth(USER_OWNER)

    # 1. Update agent settings
    res_set = client.patch(
        f"/api/admin/tenants/{TEST_TENANT}/agent-settings",
        json={"voice_persona": "friendly", "business_hours_enabled": True, "business_hours_start": "08:00", "business_hours_end": "18:00"},
        headers=headers,
    )
    assert res_set.status_code == 200
    assert res_set.json()["voice_persona"] == "friendly"

    # 2. Invite new member
    res_inv = client.post(
        f"/api/tenants/{TEST_TENANT}/members/invite",
        json={"email": "new_team@rbac.com", "role": "viewer"},
        headers=headers,
    )
    assert res_inv.status_code == 200
    assert res_inv.json()["ok"] is True

    # 3. Update member role
    res_role = client.patch(
        f"/api/tenants/{TEST_TENANT}/members/{USER_VIEWER}/role",
        json={"role": "operator"},
        headers=headers,
    )
    assert res_role.status_code == 200
    assert res_role.json()["membership"]["role"] == "operator"

    # Revert back
    client.patch(
        f"/api/tenants/{TEST_TENANT}/members/{USER_VIEWER}/role",
        json={"role": "viewer"},
        headers=headers,
    )


def test_last_active_owner_cannot_be_revoked_or_demoted(rbac_client: TestClient):
    """Assert Owner cannot revoke self, cannot revoke last active owner, and cannot demote last active owner."""
    client = rbac_client
    headers = _auth(USER_OWNER)

    # 1. Owner cannot revoke self (409 Conflict)
    res_self = client.delete(
        f"/api/tenants/{TEST_TENANT}/members/{USER_OWNER}",
        headers=headers,
    )
    assert res_self.status_code == 409
    assert "owner_cannot_revoke_self" in res_self.json()["detail"]

    # 2. Last active owner cannot be demoted to operator (409 Conflict)
    res_demote = client.patch(
        f"/api/tenants/{TEST_TENANT}/members/{USER_OWNER}/role",
        json={"role": "operator"},
        headers=headers,
    )
    assert res_demote.status_code == 409
    assert "last_active_owner_cannot_be_demoted" in res_demote.json()["detail"]

    # 3. Last active owner cannot be demoted via re-invite payload (409 Conflict)
    res_reinv_demote = client.post(
        f"/api/tenants/{TEST_TENANT}/members/invite",
        json={"email": "owner@rbac.com", "role": "viewer"},
        headers=headers,
    )
    assert res_reinv_demote.status_code == 409
    assert "last_active_owner_cannot_be_demoted" in res_reinv_demote.json()["detail"]


def test_escalation_assignment_and_resolution_invariants(rbac_client: TestClient):
    """Assert escalation assignment requires active member in same tenant, and double-close returns 409."""
    client = rbac_client
    headers = _auth(USER_OWNER)

    # 1. Assigning to non-member returns 422
    res_assign_fake = client.patch(
        f"/api/tenants/{TEST_TENANT}/escalations/call-rbac-1/assign",
        json={"assigned_to_user_id": "usr-ghost-nonmember"},
        headers=headers,
    )
    assert res_assign_fake.status_code == 422
    assert "assignee_not_active_member" in res_assign_fake.json()["detail"]

    # 2. Assigning to active member succeeds
    res_assign_ok = client.patch(
        f"/api/tenants/{TEST_TENANT}/escalations/call-rbac-1/assign",
        json={"assigned_to_user_id": USER_OPERATOR},
        headers=headers,
    )
    assert res_assign_ok.status_code == 200

    # 3. Resolving closed escalation returns 200 on first resolve
    res_resolve_1 = client.patch(
        f"/api/tenants/{TEST_TENANT}/escalations/call-rbac-1/resolve",
        json={"status": "resolved", "resolution_category": "callback_completed", "staff_resolution": "First resolution"},
        headers=headers,
    )
    assert res_resolve_1.status_code == 200

    # 4. Attempting to resolve already resolved escalation returns 409 Conflict (protects audit trail)
    res_resolve_2 = client.patch(
        f"/api/tenants/{TEST_TENANT}/escalations/call-rbac-1/resolve",
        json={"status": "resolved", "resolution_category": "callback_completed", "staff_resolution": "Second resolution"},
        headers=headers,
    )
    assert res_resolve_2.status_code == 409
    assert "escalation_already_closed" in res_resolve_2.json()["detail"]

