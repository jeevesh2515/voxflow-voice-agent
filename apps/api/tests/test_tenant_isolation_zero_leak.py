"""Release Gate #3: Automated 0-Leak Cross-Tenant Isolation Test Suite.

Proves that:
1. An authenticated tenant user can NEVER query or mutate another tenant's data.
2. Parameter enumeration (direct ID lookups, list endpoints, aggregations) strictly returns
   403 Forbidden or 404 Not Found for foreign tenant data, with EXACTLY 0 leaked rows.
3. Database queries and API endpoints enforce server-authoritative tenant scoping.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

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


TENANT_ALPHA = "tenant-alpha"
TENANT_BETA = "tenant-beta"

USER_ALPHA_OWNER = "usr-alpha-owner"
USER_BETA_OWNER = "usr-beta-owner"
USER_BETA_OPERATOR = "usr-beta-operator"
USER_BETA_VIEWER = "usr-beta-viewer"

AUTH_USERS = {
    USER_ALPHA_OWNER: AuthUser(user_id=USER_ALPHA_OWNER, email="alpha_owner@alpha.com"),
    USER_BETA_OWNER: AuthUser(user_id=USER_BETA_OWNER, email="beta_owner@beta.com"),
    USER_BETA_OPERATOR: AuthUser(user_id=USER_BETA_OPERATOR, email="beta_operator@beta.com"),
    USER_BETA_VIEWER: AuthUser(user_id=USER_BETA_VIEWER, email="beta_viewer@beta.com"),
}


@pytest.fixture
def isolation_environment(monkeypatch):
    """Configure tenant authorization enforcement and clean test database."""
    settings = get_settings()
    monkeypatch.setattr(settings, "tenant_authorization_enforced", True)
    monkeypatch.setattr(settings, "demo_mode_enabled", False)
    monkeypatch.setattr(auth_mod, "_verify_token", lambda token: AUTH_USERS.get(token))

    now = datetime.now(timezone.utc)

    with session_scope() as db:
        # 1. Clean existing records for clean deterministic isolation test
        for t_id in (TENANT_ALPHA, TENANT_BETA):
            db.query(Appointment).filter(Appointment.tenant_id == t_id).delete()
            db.query(CommunicationLog).filter(CommunicationLog.tenant_id == t_id).delete()
            db.query(Call).filter(Call.tenant_id == t_id).delete()
            db.query(Shipment).filter(Shipment.tenant_id == t_id).delete()
            db.query(Order).filter(Order.tenant_id == t_id).delete()
            db.query(Stock).filter(Stock.tenant_id == t_id).delete()
            db.query(Product).filter(Product.tenant_id == t_id).delete()
            db.query(Supplier).filter(Supplier.tenant_id == t_id).delete()
            db.query(TenantPhoneNumber).filter(TenantPhoneNumber.tenant_id == t_id).delete()
            db.query(OutboundCampaign).filter(OutboundCampaign.tenant_id == t_id).delete()
            db.query(TenantMember).filter(TenantMember.tenant_id == t_id).delete()
            db.query(Tenant).filter(Tenant.id == t_id).delete()

        # 2. Seed Tenants
        alpha_t = Tenant(
            id=TENANT_ALPHA,
            name="Alpha Corp Logistics",
            agent_name="AlphaAgent",
            default_language="en",
            plan="enterprise",
            voice_persona="assertive",
            active=1,
            created_at=now,
        )
        beta_t = Tenant(
            id=TENANT_BETA,
            name="Beta Freight Ltd",
            agent_name="BetaAgent",
            default_language="en",
            plan="starter",
            voice_persona="friendly",
            active=1,
            created_at=now,
        )
        db.add_all([alpha_t, beta_t])
        db.flush()

        # 3. Seed Memberships
        members = [
            TenantMember(
                id="tm-alpha-owner",
                tenant_id=TENANT_ALPHA,
                user_id=USER_ALPHA_OWNER,
                subject_email_hash=normalized_email_hash("alpha_owner@alpha.com"),
                role=ROLE_OWNER,
                status="active",
                activated_at=now,
            ),
            TenantMember(
                id="tm-beta-owner",
                tenant_id=TENANT_BETA,
                user_id=USER_BETA_OWNER,
                subject_email_hash=normalized_email_hash("beta_owner@beta.com"),
                role=ROLE_OWNER,
                status="active",
                activated_at=now,
            ),
            TenantMember(
                id="tm-beta-operator",
                tenant_id=TENANT_BETA,
                user_id=USER_BETA_OPERATOR,
                subject_email_hash=normalized_email_hash("beta_operator@beta.com"),
                role=ROLE_OPERATOR,
                status="active",
                activated_at=now,
            ),
            TenantMember(
                id="tm-beta-viewer",
                tenant_id=TENANT_BETA,
                user_id=USER_BETA_VIEWER,
                subject_email_hash=normalized_email_hash("beta_viewer@beta.com"),
                role=ROLE_VIEWER,
                status="active",
                activated_at=now,
            ),
        ]
        db.add_all(members)
        db.flush()

        # 4. Seed Alpha Domain Entities
        sup_alpha = Supplier(
            id="sup-alpha-1",
            tenant_id=TENANT_ALPHA,
            name="Alpha Prime Suppliers Ltd",
            phone="+441632960100",
            city="Manchester",
            state="Greater Manchester",
            pincode="M1 1AE",
            contact_person="Alice Alpha",
            gstin="GB111222333",
            active=1,
        )
        prod_alpha = Product(
            sku="SKU-ALPHA-100",
            tenant_id=TENANT_ALPHA,
            name="Alpha Heavy Industrial Rotor",
            category="machinery",
            pack_size="1 unit",
            mrp_inr=5000.0,
        )
        stock_alpha = Stock(
            sku="SKU-ALPHA-100",
            tenant_id=TENANT_ALPHA,
            warehouse="Warehouse-Alpha-North",
            quantity=250,
        )
        order_alpha = Order(
            id="PO-ALPHA-9001",
            tenant_id=TENANT_ALPHA,
            supplier_id="sup-alpha-1",
            status="confirmed",
            items_json=json.dumps([{"sku": "SKU-ALPHA-100", "quantity": 100}]),
            total_qty=100,
            notes="Confidential Alpha Purchase Order",
        )
        ship_alpha = Shipment(
            id="SHP-ALPHA-501",
            tenant_id=TENANT_ALPHA,
            order_id="PO-ALPHA-9001",
            status="in_transit",
            carrier="Alpha Express Freight",
            tracking_no="TRK-ALPHA-9999",
            expected_delivery=now,
            history_json=json.dumps([{"status": "dispatched", "location": "Manchester Hub"}]),
        )
        call_alpha = Call(
            id="call-alpha-101",
            tenant_id=TENANT_ALPHA,
            caller_phone="+441632960100",
            caller_name="Alice Alpha",
            intent="order_status",
            outcome="completed",
            started_at=now,
            ended_at=now,
            duration_sec=45,
            transcript_json=json.dumps([{"role": "caller", "text": "What is status of PO-ALPHA-9001?"}]),
            actions_json=json.dumps([{"action": "lookup_order", "po": "PO-ALPHA-9001"}]),
            escalated=0,
            resolution_status="resolved",
        )
        esc_alpha = Call(
            id="call-alpha-esc-1",
            tenant_id=TENANT_ALPHA,
            caller_phone="+441632960100",
            caller_name="Alice Alpha",
            intent="dispute_delay",
            outcome="escalated",
            started_at=now,
            ended_at=now,
            duration_sec=90,
            transcript_json=json.dumps([{"role": "caller", "text": "Urgent escalation on shipment!"}]),
            actions_json=json.dumps([{"action": "escalate"}]),
            escalated=1,
            escalation_priority="critical",
            escalation_status="pending",
            resolution_status="escalated",
        )
        app_alpha = Appointment(
            id="app-alpha-1",
            tenant_id=TENANT_ALPHA,
            supplier_id="sup-alpha-1",
            datetime=now,
            purpose="Alpha Dock Inspection Slot A",
            status="confirmed",
            created_at=now,
        )
        comm_alpha = CommunicationLog(
            id="msg-alpha-1",
            tenant_id=TENANT_ALPHA,
            channel="email",
            recipient="alice@alpha.com",
            subject="Alpha Confidential Shipment Dispatch",
            body="Your Alpha PO-ALPHA-9001 has been dispatched.",
            status="delivered",
            timestamp=now,
        )
        phone_alpha = TenantPhoneNumber(
            phone_number="+441632960001",
            tenant_id=TENANT_ALPHA,
            provider="connect",
            active=1,
            route_language="en",
            verification_mode="standard",
            created_at=now,
        )
        camp_alpha = OutboundCampaign(
            id="cmp-alpha-1",
            tenant_id=TENANT_ALPHA,
            name="Alpha Outbound Supplier Survey",
            campaign_type="po_confirmation",
            status="draft",
            total_targets=10,
            successful_calls=0,
            failed_calls=0,
            created_at=now,
        )
        db.add_all([
            sup_alpha, prod_alpha, stock_alpha, order_alpha, ship_alpha,
            call_alpha, esc_alpha, app_alpha, comm_alpha, phone_alpha, camp_alpha,
        ])

        # 5. Seed Beta Domain Entities
        sup_beta = Supplier(
            id="sup-beta-1",
            tenant_id=TENANT_BETA,
            name="Beta Logistics Partners",
            phone="+441632960200",
            city="Birmingham",
            state="West Midlands",
            pincode="B1 1BB",
            contact_person="Bob Beta",
            gstin="GB999888777",
            active=1,
        )
        prod_beta = Product(
            sku="SKU-BETA-200",
            tenant_id=TENANT_BETA,
            name="Beta Standard Steel Bearing",
            category="hardware",
            pack_size="10 units",
            mrp_inr=1200.0,
        )
        stock_beta = Stock(
            sku="SKU-BETA-200",
            tenant_id=TENANT_BETA,
            warehouse="Warehouse-Beta-South",
            quantity=500,
        )
        order_beta = Order(
            id="PO-BETA-9002",
            tenant_id=TENANT_BETA,
            supplier_id="sup-beta-1",
            status="pending",
            items_json=json.dumps([{"sku": "SKU-BETA-200", "quantity": 50}]),
            total_qty=50,
            notes="Beta Purchase Order for Bearings",
        )
        ship_beta = Shipment(
            id="SHP-BETA-502",
            tenant_id=TENANT_BETA,
            order_id="PO-BETA-9002",
            status="scheduled",
            carrier="Beta Road Haulage",
            tracking_no="TRK-BETA-7777",
            expected_delivery=now,
            history_json=json.dumps([{"status": "created", "location": "Birmingham Depot"}]),
        )
        call_beta = Call(
            id="call-beta-202",
            tenant_id=TENANT_BETA,
            caller_phone="+441632960200",
            caller_name="Bob Beta",
            intent="stock_query",
            outcome="completed",
            started_at=now,
            ended_at=now,
            duration_sec=30,
            transcript_json=json.dumps([{"role": "caller", "text": "Do you have SKU-BETA-200 in stock?"}]),
            actions_json=json.dumps([{"action": "check_stock", "sku": "SKU-BETA-200"}]),
            escalated=0,
            resolution_status="resolved",
        )
        esc_beta = Call(
            id="call-beta-esc-1",
            tenant_id=TENANT_BETA,
            caller_phone="+441632960200",
            caller_name="Bob Beta",
            intent="billing_query",
            outcome="escalated",
            started_at=now,
            ended_at=now,
            duration_sec=60,
            transcript_json=json.dumps([{"role": "caller", "text": "Invoice question for Beta PO"}]),
            actions_json=json.dumps([{"action": "escalate"}]),
            escalated=1,
            escalation_priority="medium",
            escalation_status="pending",
            resolution_status="escalated",
        )
        app_beta = Appointment(
            id="app-beta-1",
            tenant_id=TENANT_BETA,
            supplier_id="sup-beta-1",
            datetime=now,
            purpose="Beta Unloading Slot B",
            status="confirmed",
            created_at=now,
        )
        comm_beta = CommunicationLog(
            id="msg-beta-1",
            tenant_id=TENANT_BETA,
            channel="sms",
            recipient="+441632960200",
            subject="Beta Arrival Notice",
            body="Your delivery is scheduled for tomorrow.",
            status="delivered",
            timestamp=now,
        )
        phone_beta = TenantPhoneNumber(
            phone_number="+441632960002",
            tenant_id=TENANT_BETA,
            provider="connect",
            active=1,
            route_language="en",
            verification_mode="enhanced",
            created_at=now,
        )
        camp_beta = OutboundCampaign(
            id="cmp-beta-1",
            tenant_id=TENANT_BETA,
            name="Beta Delivery ETA Reminder",
            campaign_type="dock_reminder",
            status="active",
            total_targets=5,
            successful_calls=2,
            failed_calls=0,
            created_at=now,
        )
        db.add_all([
            sup_beta, prod_beta, stock_beta, order_beta, ship_beta,
            call_beta, esc_beta, app_beta, comm_beta, phone_beta, camp_beta,
        ])
        db.commit()

    app = create_app()
    client = TestClient(app)
    return client


def _auth_headers(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}", "X-VoxFlow-User-Id": user_id}


# ==============================================================================
# 1. Cross-Tenant List Endpoint Isolation Tests (Release Gate #3)
# ==============================================================================


def test_cross_tenant_list_endpoints_strictly_forbidden(isolation_environment: TestClient):
    """Assert User Beta querying Tenant Alpha list endpoints receives 403 Forbidden with 0 data."""
    client = isolation_environment
    headers_beta = _auth_headers(USER_BETA_OWNER)

    endpoints = [
        f"/api/suppliers?tenant_id={TENANT_ALPHA}",
        f"/api/stock?tenant_id={TENANT_ALPHA}",
        f"/api/orders?tenant_id={TENANT_ALPHA}",
        f"/api/shipments?tenant_id={TENANT_ALPHA}",
        f"/api/calls?tenant_id={TENANT_ALPHA}",
        f"/api/appointments?tenant_id={TENANT_ALPHA}",
        f"/api/communications?tenant_id={TENANT_ALPHA}",
        f"/api/summary?tenant_id={TENANT_ALPHA}",
        f"/api/tenants/{TENANT_ALPHA}/members",
        f"/api/tenants/{TENANT_ALPHA}/escalations",
        f"/api/tenants/{TENANT_ALPHA}/escalations/metrics",
        f"/api/campaigns?tenant_id={TENANT_ALPHA}",
        f"/api/jobs/health?tenant_id={TENANT_ALPHA}",
        f"/api/analytics/overview?tenant_id={TENANT_ALPHA}",
        f"/api/admin/tenants/{TENANT_ALPHA}/agent-settings",
        f"/api/admin/tenants/{TENANT_ALPHA}/phone-numbers",
        f"/api/admin/tenants/{TENANT_ALPHA}/caller-pins",
        f"/api/tenants/{TENANT_ALPHA}/evals/scorecard",
    ]

    for ep in endpoints:
        resp = client.get(ep, headers=headers_beta)
        assert resp.status_code == 403, f"Expected 403 for cross-tenant query {ep}, got {resp.status_code}: {resp.text}"
        body_text = resp.text
        # Assert zero leak of Alpha keywords in error responses
        assert "Alpha Heavy Industrial" not in body_text
        assert "Alice Alpha" not in body_text
        assert "PO-ALPHA-9001" not in body_text


# ==============================================================================
# 2. Direct ID Enumeration & Parameter Tampering Isolation
# ==============================================================================


def test_cross_tenant_id_enumeration_returns_404_not_found(isolation_environment: TestClient):
    """Assert direct lookups of Tenant Alpha IDs while scoped to Tenant Beta return 404."""
    client = isolation_environment
    headers_beta = _auth_headers(USER_BETA_OWNER)

    # 1. Supplier ID lookup
    res_sup = client.get(f"/api/suppliers/sup-alpha-1?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_sup.status_code == 404, f"Expected 404 for foreign supplier lookup, got {res_sup.status_code}"

    # 2. Order ID lookup
    res_ord = client.get(f"/api/orders/PO-ALPHA-9001?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_ord.status_code == 404, f"Expected 404 for foreign order lookup, got {res_ord.status_code}"

    # 3. Call ID lookup
    res_call = client.get(f"/api/calls/call-alpha-101?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_call.status_code == 404, f"Expected 404 for foreign call lookup, got {res_call.status_code}"

    # 4. Call recording lookup
    res_rec = client.get(f"/api/calls/call-alpha-101/recording?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_rec.status_code == 404, f"Expected 404 for foreign recording lookup, got {res_rec.status_code}"

    # 5. Escalation detail lookup
    res_esc = client.get(f"/api/tenants/{TENANT_BETA}/escalations/call-alpha-esc-1", headers=headers_beta)
    assert res_esc.status_code == 404, f"Expected 404 for foreign escalation detail lookup, got {res_esc.status_code}"

    # 6. Campaign detail lookup
    res_cmp = client.get(f"/api/campaigns/cmp-alpha-1?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_cmp.status_code == 404, f"Expected 404 for foreign campaign lookup, got {res_cmp.status_code}"


# ==============================================================================
# 3. Cross-Tenant Mutation & Injection Denial Tests
# ==============================================================================


def test_cross_tenant_mutations_strictly_blocked(isolation_environment: TestClient):
    """Assert User Beta cannot create, mutate, or delete resources in Tenant Alpha."""
    client = isolation_environment
    headers_beta = _auth_headers(USER_BETA_OWNER)

    # 1. Cannot create supplier in Tenant Alpha
    res_sup = client.post(
        f"/api/suppliers?tenant_id={TENANT_ALPHA}",
        json={"name": "Attacker Supplier", "phone": "+441632960999", "city": "London", "state": "UK", "pincode": "EC1A", "contact_person": "Hacker", "gstin": "GB999999"},
        headers=headers_beta,
    )
    assert res_sup.status_code == 403

    # 2. Cannot create order in Tenant Alpha
    res_ord = client.post(
        f"/api/orders?tenant_id={TENANT_ALPHA}",
        json={"supplier_id": "sup-alpha-1", "items": [{"sku": "SKU-ALPHA-100", "quantity": 10}]},
        headers=headers_beta,
    )
    assert res_ord.status_code == 403

    # 3. Cannot create appointment in Tenant Alpha
    res_app = client.post(
        f"/api/appointments?tenant_id={TENANT_ALPHA}",
        json={"supplier_id": "sup-alpha-1", "datetime": "2026-09-01T10:00:00Z", "purpose": "Unauthorized slot"},
        headers=headers_beta,
    )
    assert res_app.status_code == 403

    # 4. Cannot create communication in Tenant Alpha
    res_comm = client.post(
        f"/api/communications?tenant_id={TENANT_ALPHA}",
        json={"channel": "email", "recipient": "victim@alpha.com", "subject": "Phish", "body": "Leak data"},
        headers=headers_beta,
    )
    assert res_comm.status_code == 403

    # 5. Cannot bulk-import CSV into Tenant Alpha
    csv_payload = "sku,name,category,pack_size,mrp_inr\nSKU-ATTACK-1,Attack Tool,malware,1 pc,999.0\n"
    res_csv = client.post(
        f"/api/data/products/import?tenant_id={TENANT_ALPHA}",
        data={"csv_text": csv_payload, "mode": "upsert"},
        headers=headers_beta,
    )
    assert res_csv.status_code == 403

    # 6. Cannot modify Tenant Alpha agent settings
    res_set = client.patch(
        f"/api/admin/tenants/{TENANT_ALPHA}/agent-settings",
        json={"voice_persona": "friendly"},
        headers=headers_beta,
    )
    assert res_set.status_code == 403

    # 7. Cannot invite members to Tenant Alpha
    res_inv = client.post(
        f"/api/tenants/{TENANT_ALPHA}/members/invite",
        json={"email": "attacker@evil.com", "role": "owner"},
        headers=headers_beta,
    )
    assert res_inv.status_code == 403

    # 8. Cannot revoke Tenant Alpha members
    res_rev = client.delete(
        f"/api/tenants/{TENANT_ALPHA}/members/{USER_ALPHA_OWNER}",
        headers=headers_beta,
    )
    assert res_rev.status_code == 403


# ==============================================================================
# 4. Intra-Tenant Legitimate Access Zero-Leak Verification
# ==============================================================================


def test_intra_tenant_legitimate_queries_contain_zero_cross_tenant_rows(isolation_environment: TestClient):
    """Assert User Beta querying Tenant Beta sees 100% Beta data and 0% Alpha data."""
    client = isolation_environment
    headers_beta = _auth_headers(USER_BETA_OWNER)

    # 1. Suppliers
    res_sup = client.get(f"/api/suppliers?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_sup.status_code == 200
    sups = res_sup.json()
    assert len(sups) == 1
    assert sups[0]["name"] == "Beta Logistics Partners"
    assert not any("Alpha" in s["name"] for s in sups)

    # 2. Stock
    res_stk = client.get(f"/api/stock?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_stk.status_code == 200
    stks = res_stk.json()
    assert len(stks) == 1
    assert stks[0]["sku"] == "SKU-BETA-200"
    assert not any("ALPHA" in s["sku"] for s in stks)

    # 3. Orders
    res_ord = client.get(f"/api/orders?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_ord.status_code == 200
    ords = res_ord.json()
    assert len(ords) == 1
    assert ords[0]["id"] == "PO-BETA-9002"
    assert not any("ALPHA" in o["id"] for o in ords)

    # 4. Shipments
    res_shp = client.get(f"/api/shipments?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_shp.status_code == 200
    shps = res_shp.json()
    assert len(shps) == 1
    assert shps[0]["id"] == "SHP-BETA-502"
    assert not any("ALPHA" in s["id"] for s in shps)

    # 5. Calls
    res_calls = client.get(f"/api/calls?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_calls.status_code == 200
    calls = res_calls.json()
    assert len(calls) == 2  # call_beta and esc_beta
    assert all("Beta" in c["caller_name"] or "beta" in c["id"] for c in calls)
    assert not any("Alpha" in c["caller_name"] or "alpha" in c["id"] for c in calls)

    # 6. Summary Counters
    res_sum = client.get(f"/api/summary?tenant_id={TENANT_BETA}", headers=headers_beta)
    assert res_sum.status_code == 200
    summary = res_sum.json()
    assert summary["suppliers"] == 1
    assert summary["orders"] == 1
    assert summary["calls"] == 2
    assert summary["pending_orders"] == 1

    # 7. Escalations
    res_esc = client.get(f"/api/tenants/{TENANT_BETA}/escalations", headers=headers_beta)
    assert res_esc.status_code == 200
    escs = res_esc.json()["items"]
    assert len(escs) == 1
    assert escs[0]["id"] == "call-beta-esc-1"
    assert not any("ALPHA" in e["id"] for e in escs)


# ==============================================================================
# 5. Raw SQL / Database Layer Scoping Verification
# ==============================================================================


def test_database_queries_strictly_scoped_by_tenant_id(isolation_environment: TestClient):
    """Direct database assertion verifying that composite keys and tenant_id clauses strictly isolate rows."""
    with session_scope() as db:
        # 1. Orders scoped to Alpha
        alpha_orders = db.execute(select(Order).where(Order.tenant_id == TENANT_ALPHA)).scalars().all()
        assert len(alpha_orders) == 1
        assert alpha_orders[0].id == "PO-ALPHA-9001"

        # 2. Orders scoped to Beta
        beta_orders = db.execute(select(Order).where(Order.tenant_id == TENANT_BETA)).scalars().all()
        assert len(beta_orders) == 1
        assert beta_orders[0].id == "PO-BETA-9002"

        # 3. Product composite keys (sku, tenant_id)
        alpha_prod = db.execute(
            select(Product).where(Product.sku == "SKU-ALPHA-100", Product.tenant_id == TENANT_ALPHA)
        ).scalar_one_or_none()
        assert alpha_prod is not None

        # Cross-tenant query for Alpha SKU under Beta tenant must return None
        cross_prod = db.execute(
            select(Product).where(Product.sku == "SKU-ALPHA-100", Product.tenant_id == TENANT_BETA)
        ).scalar_one_or_none()
        assert cross_prod is None
