"""Automated test suite for Day 48 Closed-Loop Escalation Ownership, SLAs, and Resolution."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from voxflow_api import auth
from voxflow_api.config import get_settings
from voxflow_api.db import Call, Tenant, TenantMember, reset_db, session_scope
from voxflow_api.main import create_app
from voxflow_api.services.escalation_service import (
    compute_sla_due_at,
    derive_escalation_priority,
    get_escalation_kpis,
    init_call_escalation,
)
from voxflow_api.auth import AuthUser, normalized_email_hash


IDENTITIES = {
    "owner-token": auth.AuthUser(
        user_id="day48-owner",
        email="owner@day48.test",
        tenant_id="varun",
        role="owner",
        identity_verified=True,
    ),
    "operator-token": auth.AuthUser(
        user_id="day48-operator",
        email="operator@day48.test",
        tenant_id="varun",
        role="operator",
        identity_verified=True,
    ),
    "viewer-token": auth.AuthUser(
        user_id="day48-viewer",
        email="viewer@day48.test",
        tenant_id="varun",
        role="viewer",
        identity_verified=True,
    ),
    "amul-owner-token": auth.AuthUser(
        user_id="day48-amul-owner",
        email="amul-owner@day48.test",
        tenant_id="amul",
        role="owner",
        identity_verified=True,
    ),
}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _membership(member_id: str, tenant_id: str, user_id: str, email: str, role: str) -> TenantMember:
    return TenantMember(
        id=member_id,
        tenant_id=tenant_id,
        user_id=user_id,
        subject_email_hash=normalized_email_hash(email, fallback_subject=user_id),
        role=role,
        status="active",
        invited_by="day48-test",
        activated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def day48_client(monkeypatch):
    """Isolated test client with ephemeral database and mocked auth identities."""
    monkeypatch.setenv("TENANT_AUTHORIZATION_ENFORCED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(auth, "_verify_token", lambda token: IDENTITIES.get(token))

    reset_db()
    with session_scope() as db:
        db.add(
            Tenant(
                id="varun",
                name="Varun Beverages",
                plan="pro",
                default_language="en",
                escalation_sla_minutes=60,
            )
        )
        db.add(
            Tenant(
                id="amul",
                name="Amul Dairy",
                plan="pro",
                default_language="en",
            )
        )
        db.add_all(
            [
                _membership("mem-owner", "varun", "day48-owner", "owner@day48.test", "owner"),
                _membership("mem-op", "varun", "day48-operator", "operator@day48.test", "operator"),
                _membership("mem-view", "varun", "day48-viewer", "viewer@day48.test", "viewer"),
                _membership("mem-amul-owner", "amul", "day48-amul-owner", "amul-owner@day48.test", "owner"),
            ]
        )

    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


def test_sla_due_at_computation():
    """Verify priority-based SLA calculation."""
    base_time = datetime(2026, 8, 28, 10, 0, 0, tzinfo=timezone.utc)

    # Critical: 15 mins
    crit = compute_sla_due_at("critical", base_sla_minutes=60, from_time=base_time)
    assert crit == base_time + timedelta(minutes=15)

    # High: 30 mins
    high = compute_sla_due_at("high", base_sla_minutes=60, from_time=base_time)
    assert high == base_time + timedelta(minutes=30)

    # Medium: base (60 mins)
    med = compute_sla_due_at("medium", base_sla_minutes=60, from_time=base_time)
    assert med == base_time + timedelta(minutes=60)

    # Low: 4x base (240 mins)
    low = compute_sla_due_at("low", base_sla_minutes=60, from_time=base_time)
    assert low == base_time + timedelta(minutes=240)


def test_derive_escalation_priority():
    """Verify priority derivation from caller context."""
    # Critical keywords
    assert derive_escalation_priority(reason="Urgent accident and damaged shipment") == "critical"
    assert derive_escalation_priority(reason="Potential fraud reported on order") == "critical"

    # Unhappy satisfaction -> High
    assert derive_escalation_priority(satisfaction="unhappy", reason="Delayed delivery") == "high"

    # Follow up required -> Medium
    assert derive_escalation_priority(follow_up_required=True, reason="Standard quote follow-up") == "medium"

    # Default -> Medium
    assert derive_escalation_priority() == "medium"


def test_init_call_escalation():
    """Verify initializing escalation on a Call object."""
    now = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)
    call = Call(
        id="call-init-test",
        tenant_id="varun",
        started_at=now,
        caller_phone="+447700900123",
        caller_name="Alice Smith",
        satisfaction="unhappy",
        reason="Missing package",
    )
    tenant = Tenant(id="varun", name="Test", escalation_sla_minutes=60)

    init_call_escalation(call, tenant)
    assert call.escalated == 1
    assert call.escalation_status == "pending"
    assert call.escalation_priority == "high"
    assert call.sla_due_at == now + timedelta(minutes=30)


def test_list_escalations_and_filtering(day48_client: TestClient):
    """Test listing escalations with status, priority, and search filters."""
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.add(
            Call(
                id="call-esc-001",
                tenant_id="varun",
                started_at=now - timedelta(minutes=40),
                caller_phone="+447700900111",
                caller_name="David Brown",
                reason="Damaged cargo on arrival",
                escalated=1,
                escalation_priority="critical",
                escalation_status="pending",
                sla_due_at=now - timedelta(minutes=25),  # Breached
            )
        )
        db.add(
            Call(
                id="call-esc-002",
                tenant_id="varun",
                started_at=now - timedelta(minutes=15),
                caller_phone="+447700900222",
                caller_name="Sarah Miller",
                reason="Invoice discrepancy",
                escalated=1,
                escalation_priority="medium",
                escalation_status="in_progress",
                assigned_to_user_id="day48-operator",
                sla_due_at=now + timedelta(minutes=45),  # Active
            )
        )
        db.add(
            Call(
                id="call-esc-003",
                tenant_id="varun",
                started_at=now - timedelta(hours=2),
                caller_phone="+447700900333",
                caller_name="John Doe",
                reason="Address update request",
                escalated=1,
                escalation_priority="low",
                escalation_status="resolved",
                staff_resolution="Updated shipping address in ERP.",
                staff_resolved_at=now - timedelta(hours=1),
                resolution_category="order_updated",
                sla_due_at=now + timedelta(hours=2),
            )
        )

    # 1. List all
    res = day48_client.get(
        "/api/tenants/varun/escalations",
        headers=_headers("owner-token"),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # 2. Filter by status: pending
    res_pend = day48_client.get(
        "/api/tenants/varun/escalations?status=pending",
        headers=_headers("operator-token"),
    )
    assert res_pend.status_code == 200
    items_pend = res_pend.json()["items"]
    assert len(items_pend) == 1
    assert items_pend[0]["id"] == "call-esc-001"

    # 3. Filter by priority: critical
    res_crit = day48_client.get(
        "/api/tenants/varun/escalations?priority=critical",
        headers=_headers("viewer-token"),
    )
    assert res_crit.status_code == 200
    assert len(res_crit.json()["items"]) == 1

    # 4. Filter by breached_only: true
    res_breach = day48_client.get(
        "/api/tenants/varun/escalations?breached_only=true",
        headers=_headers("owner-token"),
    )
    assert res_breach.status_code == 200
    assert len(res_breach.json()["items"]) == 1
    assert res_breach.json()["items"][0]["id"] == "call-esc-001"

    # 5. Search query
    res_search = day48_client.get(
        "/api/tenants/varun/escalations?search=Sarah",
        headers=_headers("operator-token"),
    )
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) == 1
    assert res_search.json()["items"][0]["caller_name"] == "Sarah Miller"


def test_escalation_metrics(day48_client: TestClient):
    """Test escalation KPI metrics computation."""
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.add(
            Call(
                id="call-m-1",
                tenant_id="varun",
                started_at=now - timedelta(minutes=30),
                caller_phone="+447700900111",
                caller_name="Caller One",
                reason="Issue",
                escalated=1,
                escalation_priority="critical",
                escalation_status="pending",
                sla_due_at=now - timedelta(minutes=15),  # Breached
            )
        )
        db.add(
            Call(
                id="call-m-2",
                tenant_id="varun",
                started_at=now - timedelta(minutes=10),
                caller_phone="+447700900222",
                caller_name="Caller Two",
                reason="Issue 2",
                escalated=1,
                escalation_priority="medium",
                escalation_status="in_progress",
                sla_due_at=now + timedelta(minutes=50),
            )
        )
        db.add(
            Call(
                id="call-m-3",
                tenant_id="varun",
                started_at=now - timedelta(hours=1),
                caller_phone="+447700900333",
                caller_name="Caller Three",
                reason="Issue 3",
                escalated=1,
                escalation_priority="low",
                escalation_status="resolved",
                staff_resolution="Resolved satisfactorily.",
                staff_resolved_at=now - timedelta(minutes=30),
                sla_due_at=now + timedelta(hours=3),
            )
        )

    res = day48_client.get(
        "/api/tenants/varun/escalations/metrics",
        headers=_headers("viewer-token"),
    )
    assert res.status_code == 200
    kpis = res.json()
    assert kpis["tenant_id"] == "varun"
    assert kpis["total_escalations"] == 3
    assert kpis["pending_count"] == 1
    assert kpis["in_progress_count"] == 1
    assert kpis["resolved_count"] == 1
    assert kpis["breached_count"] == 1
    assert kpis["sla_compliance_rate"] == 100.0
    assert kpis["avg_resolution_min"] > 0


def test_assign_and_claim_escalation(day48_client: TestClient):
    """Test assigning an escalation to a user and self-claiming."""
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.add(
            Call(
                id="call-assign-test",
                tenant_id="varun",
                started_at=now,
                caller_phone="+447700900888",
                caller_name="Mark Evans",
                reason="Technical issue",
                escalated=1,
                escalation_status="pending",
                escalation_priority="medium",
            )
        )

    # Assign ticket
    res = day48_client.patch(
        "/api/tenants/varun/escalations/call-assign-test/assign",
        headers=_headers("operator-token"),
        json={"assigned_to_user_id": "day48-operator"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["assigned_to_user_id"] == "day48-operator"
    assert data["escalation_status"] == "in_progress"
    assert data["assigned_at"] is not None


def test_resolve_escalation(day48_client: TestClient):
    """Test resolving an escalation ticket with category and notes."""
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.add(
            Call(
                id="call-resolve-test",
                tenant_id="varun",
                started_at=now,
                caller_phone="+447700900999",
                caller_name="Emma Watson",
                reason="Wrong items delivered",
                escalated=1,
                escalation_status="in_progress",
                escalation_priority="high",
            )
        )

    # Resolve ticket
    res = day48_client.patch(
        "/api/tenants/varun/escalations/call-resolve-test/resolve",
        headers=_headers("operator-token"),
        json={
            "status": "resolved",
            "resolution_category": "order_updated",
            "staff_resolution": "Contacted warehouse, replacement shipment dispatched via express courier.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["escalation_status"] == "resolved"
    assert data["resolution_category"] == "order_updated"
    assert data["staff_resolution"].startswith("Contacted warehouse")
    assert data["staff_resolved_at"] is not None
    assert data["resolved_by_user_id"] == "day48-operator"


def test_escalation_validation_errors(day48_client: TestClient):
    """Test validation errors for invalid priority and resolution values."""
    # Invalid priority
    res_pri = day48_client.get(
        "/api/tenants/varun/escalations?priority=extreme",
        headers=_headers("owner-token"),
    )
    assert res_pri.status_code == 422
    assert "invalid_priority" in res_pri.json()["detail"]

    # Invalid status on resolve
    res_stat = day48_client.patch(
        "/api/tenants/varun/escalations/call-resolve-test/resolve",
        headers=_headers("owner-token"),
        json={"status": "closed", "resolution_category": "callback_completed"},
    )
    assert res_stat.status_code == 422
    assert "invalid_status" in res_stat.json()["detail"]


def test_cross_tenant_isolation(day48_client: TestClient):
    """Verify strict tenant isolation for escalation data."""
    # Create call in varun
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.add(
            Call(
                id="call-iso-1",
                tenant_id="varun",
                started_at=now,
                caller_phone="+447700900111",
                caller_name="Private Caller",
                reason="Private issue",
                escalated=1,
                escalation_priority="high",
                escalation_status="pending",
            )
        )

    # Amul owner cannot access Varun call
    res = day48_client.get(
        "/api/tenants/varun/escalations/call-iso-1",
        headers=_headers("amul-owner-token"),
    )
    assert res.status_code == 403

    # Amul owner querying Amul escalations does not see Varun call
    res_amul = day48_client.get(
        "/api/tenants/amul/escalations",
        headers=_headers("amul-owner-token"),
    )
    assert res_amul.status_code == 200
    assert res_amul.json()["total"] == 0


def test_get_escalation_detail(day48_client: TestClient):
    """Test fetching full escalation item detail."""
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.add(
            Call(
                id="call-detail-test",
                tenant_id="varun",
                started_at=now,
                caller_phone="+447700900555",
                caller_name="Detail Caller",
                reason="Detailed issue with SKU-123",
                solution="Checked inventory and confirmed stock.",
                transcript_json='[{"role":"caller","text":"Where is my order?","at":"2026-08-28T10:00:00Z"}]',
                actions_json='[{"name":"get_order_details","args":{"order_id":"PO-1"},"at":1717000000}]',
                escalated=1,
                escalation_priority="high",
                escalation_status="pending",
            )
        )

    res = day48_client.get(
        "/api/tenants/varun/escalations/call-detail-test",
        headers=_headers("operator-token"),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "call-detail-test"
    assert data["caller_name"] == "Detail Caller"
    assert len(data["transcript"]) == 1
    assert data["transcript"][0]["role"] == "caller"
    assert len(data["actions"]) == 1
    assert data["actions"][0]["name"] == "get_order_details"


def test_dismiss_escalation(day48_client: TestClient):
    """Test dismissing a spam or duplicate escalation."""
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.add(
            Call(
                id="call-dismiss-test",
                tenant_id="varun",
                started_at=now,
                caller_phone="+447700900666",
                caller_name="Spam Caller",
                reason="Robocall spam",
                escalated=1,
                escalation_priority="low",
                escalation_status="pending",
            )
        )

    res = day48_client.patch(
        "/api/tenants/varun/escalations/call-dismiss-test/resolve",
        headers=_headers("owner-token"),
        json={
            "status": "dismissed",
            "resolution_category": "duplicate_or_invalid",
            "staff_resolution": "Identified as automated robocall spam. Dismissed.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["escalation_status"] == "dismissed"
    assert data["resolution_category"] == "duplicate_or_invalid"


def test_unassign_escalation(day48_client: TestClient):
    """Test unassigning a previously claimed ticket."""
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.add(
            Call(
                id="call-unassign-test",
                tenant_id="varun",
                started_at=now,
                caller_phone="+447700900777",
                caller_name="Claimed Caller",
                reason="Issue",
                escalated=1,
                escalation_priority="medium",
                escalation_status="in_progress",
                assigned_to_user_id="day48-operator",
            )
        )

    res = day48_client.patch(
        "/api/tenants/varun/escalations/call-unassign-test/assign",
        headers=_headers("owner-token"),
        json={"assigned_to_user_id": None},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["assigned_to_user_id"] is None
    assert data["assigned_at"] is None


def test_viewer_cannot_mutate_escalations(day48_client: TestClient):
    """Test that viewer role receives 403 when attempting mutation."""
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        db.add(
            Call(
                id="call-viewer-rbac-test",
                tenant_id="varun",
                started_at=now,
                caller_phone="+447700900999",
                reason="Viewer RBAC test",
                escalated=1,
                escalation_status="pending",
            )
        )

    # Viewer cannot assign
    res_assign = day48_client.patch(
        "/api/tenants/varun/escalations/call-viewer-rbac-test/assign",
        headers=_headers("viewer-token"),
        json={"assigned_to_user_id": "day48-viewer"},
    )
    assert res_assign.status_code == 403

    # Viewer cannot resolve
    res_resolve = day48_client.patch(
        "/api/tenants/varun/escalations/call-viewer-rbac-test/resolve",
        headers=_headers("viewer-token"),
        json={"status": "resolved", "staff_resolution": "Attempted by viewer."},
    )
    assert res_resolve.status_code == 403
