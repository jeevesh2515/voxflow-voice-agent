"""Tests for SaaS multi-tenancy, dynamic prompts, admin routes, and outbound webhooks."""

import pytest
from fastapi.testclient import TestClient
from voxflow_api.agent.prompts import build_system_prompt, build_tenant_prompt
from voxflow_api.db import Tenant, TenantPhoneNumber, reset_db, session_scope
from voxflow_api.integrations.webhooks import _compute_signature, dispatch_webhook
from voxflow_api.main import create_app
from voxflow_api.seed import seed


@pytest.fixture
def client():
    reset_db()
    seed(reset=True)
    app = create_app()
    return TestClient(app)


def test_build_tenant_prompt_customization():
    """Verify tenant prompt dynamically reflects custom agent name and guidelines."""
    class MockTenant:
        name = "Acme Global Logistics"
        agent_name = "Alex"
        default_language = "en"
        system_prompt_override = "Always ask for account reference before anything else."

    prompt = build_tenant_prompt(MockTenant())
    assert "You are Alex" in prompt
    assert "Acme Global Logistics" in prompt
    assert "English" in prompt
    assert "Always ask for account reference before anything else." in prompt


def test_admin_tenant_crud_and_phone_mapping(client):
    """Test creating a tenant, updating its prompt, and mapping a phone number."""
    tenant_id = "test_acme_corp"

    # 1. Create Tenant
    create_resp = client.post(
        "/api/admin/tenants",
        json={
            "id": tenant_id,
            "name": "Acme Corp Demo",
            "agent_name": "Sara",
            "default_language": "en",
            "plan": "enterprise",
            "webhook_url": "https://api.acmecorp.com/webhooks",
        },
    )
    assert create_resp.status_code == 200
    data = create_resp.json()
    assert data["tenant_id"] == tenant_id
    assert data["name"] == "Acme Corp Demo"

    # 2. Get Tenant
    get_resp = client.get(f"/api/admin/tenants/{tenant_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["agent_name"] == "Sara"

    # 3. Patch Tenant
    patch_resp = client.patch(
        f"/api/admin/tenants/{tenant_id}",
        json={"system_prompt_override": "Custom rule for Acme"},
    )
    assert patch_resp.status_code == 200

    # 4. Map Phone Number
    phone = "+15559876543"
    map_resp = client.post(
        f"/api/admin/tenants/{tenant_id}/phone-numbers",
        json={"phone_number": phone, "label": "Acme Primary Line"},
    )
    assert map_resp.status_code == 200
    assert map_resp.json()["phone_number"] == phone

    # Verify in DB
    with session_scope() as db:
        tpn = db.get(TenantPhoneNumber, phone)
        assert tpn is not None
        assert tpn.tenant_id == tenant_id

    # 5. Usage stats endpoint
    usage_resp = client.get(f"/api/admin/tenants/{tenant_id}/usage")
    assert usage_resp.status_code == 200
    assert "total_calls" in usage_resp.json()
    assert "estimated_bill_usd" in usage_resp.json()


def test_webhook_signature_generation():
    """Verify HMAC-SHA256 signature computation for webhooks."""
    secret = "whsec_test_secret_12345"
    payload = b'{"event":"order_created","data":{"id":"PO-123"}}'
    sig = _compute_signature(secret, payload)
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA256 hex string length
