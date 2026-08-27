"""Tests for Day 44 Self-Serve Signup and Centralized Tenant Provisioning."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from voxflow_api.auth import ROLE_OWNER, normalized_email_hash
from voxflow_api.config import get_settings
from voxflow_api.db import (
    Order,
    Product,
    Shipment,
    Stock,
    Supplier,
    Tenant,
    TenantMember,
    TenantPhoneNumber,
    reset_db,
    session_scope,
)
from voxflow_api.main import create_app
from voxflow_api.services.provisioning import (
    generate_unique_tenant_slug,
    provision_tenant,
    sanitize_slug,
)


@pytest.fixture(autouse=True)
def _setup_db():
    reset_db()
    yield
    reset_db()


@pytest.fixture
def client():
    return TestClient(create_app())


def test_sanitize_and_generate_unique_tenant_slug():
    assert sanitize_slug("Acme Logistics & Freight Pvt Ltd") == "acme-logistics-freight-pvt-ltd"
    assert sanitize_slug("  Apex_Transport 2026!  ") == "apex-transport-2026"
    assert sanitize_slug("!!!") == "workspace"

    with session_scope() as db:
        slug1 = generate_unique_tenant_slug(db, "Global Freight")
        assert slug1 == "global-freight"

        # Create tenant with slug1
        db.add(Tenant(id=slug1, name="Global Freight"))
        db.flush()

        slug2 = generate_unique_tenant_slug(db, "Global Freight")
        assert slug2 == "global-freight-2"

        # Create tenant with slug2
        db.add(Tenant(id=slug2, name="Global Freight 2"))
        db.flush()

        slug3 = generate_unique_tenant_slug(db, "Global Freight")
        assert slug3 == "global-freight-3"


def test_provision_tenant_service_creates_isolated_tenant_and_owner_member():
    with session_scope() as db:
        res = provision_tenant(
            db,
            name="Apex Cold Chain UK Ltd",
            owner_user_id="usr-apex-owner-1",
            owner_email="ops@apexcoldchain.co.uk",
            agent_name="Sara",
            default_language="en",
            plan="enterprise",
            phone_number="+447700900555",
            phone_label="Apex Main Line",
            seed_starter_data=True,
            invited_by="test_harness",
        )

        assert res["ok"] is True
        assert res["tenant_id"] == "apex-cold-chain-uk-ltd"
        assert res["name"] == "Apex Cold Chain UK Ltd"
        assert res["agent_name"] == "Sara"
        assert res["default_language"] == "en"
        assert res["plan"] == "enterprise"
        assert res["owner_user_id"] == "usr-apex-owner-1"
        assert res["owner_membership_created"] is True
        assert res["starter_data_seeded"] is True

        # Verify DB records
        tenant = db.get(Tenant, "apex-cold-chain-uk-ltd")
        assert tenant is not None
        assert tenant.agent_name == "Sara"
        assert tenant.default_language == "en"
        assert tenant.plan == "enterprise"
        assert tenant.active == 1

        # Verify Owner Member
        member = (
            db.execute(select(TenantMember).where(TenantMember.tenant_id == "apex-cold-chain-uk-ltd"))
            .scalars()
            .first()
        )
        assert member is not None
        assert member.user_id == "usr-apex-owner-1"
        assert member.role == ROLE_OWNER
        assert member.status == "active"
        assert member.subject_email_hash == normalized_email_hash("ops@apexcoldchain.co.uk")

        # Verify Phone Mapping
        phone = db.get(TenantPhoneNumber, "+447700900555")
        assert phone is not None
        assert phone.tenant_id == "apex-cold-chain-uk-ltd"
        # Provisioning must assign the only inbound provider with a live
        # resolution route; otherwise the line would silently never ring.
        assert phone.provider == "connect"

        # Verify Seeded Catalog
        products = (
            db.execute(select(Product).where(Product.tenant_id == "apex-cold-chain-uk-ltd"))
            .scalars()
            .all()
        )
        assert len(products) == 3

        stock = (
            db.execute(select(Stock).where(Stock.tenant_id == "apex-cold-chain-uk-ltd"))
            .scalars()
            .all()
        )
        assert len(stock) == 3

        suppliers = (
            db.execute(select(Supplier).where(Supplier.tenant_id == "apex-cold-chain-uk-ltd"))
            .scalars()
            .all()
        )
        assert len(suppliers) == 1

        orders = (
            db.execute(select(Order).where(Order.tenant_id == "apex-cold-chain-uk-ltd"))
            .scalars()
            .all()
        )
        assert len(orders) == 1

        shipments = (
            db.execute(select(Shipment).where(Shipment.tenant_id == "apex-cold-chain-uk-ltd"))
            .scalars()
            .all()
        )
        assert len(shipments) == 1


def test_post_auth_signup_endpoint_creates_workspace(client):
    payload = {
        "company_name": "Zenith Freight Solutions Ltd",
        "email": "director@zenithfreight.co.uk",
        "name": "David Miller",
        "default_language": "en",
        "seed_starter_data": True,
    }

    r = client.post("/api/auth/signup", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["tenant_id"] == "zenith-freight-solutions-ltd"
    assert data["name"] == "Zenith Freight Solutions Ltd"
    assert data["owner_membership_created"] is True
    assert data["owner_user_id"].startswith("pending-signup-")
    assert data["starter_data_seeded"] is True


def test_anonymous_signup_collision_creates_new_tenant_without_touching_existing(client):
    with session_scope() as db:
        db.add(
            Tenant(
                id="protected-workspace",
                name="Protected Workspace",
                agent_name="Original Agent",
                default_language="hi",
                plan="enterprise",
            )
        )
        db.add(
            TenantMember(
                id="tm-protected-owner",
                tenant_id="protected-workspace",
                user_id="protected-owner",
                subject_email_hash=normalized_email_hash("owner@protected.test"),
                role=ROLE_OWNER,
                status="active",
                invited_by="platform_admin",
            )
        )

    response = client.post(
        "/api/auth/signup",
        json={
            "company_name": "Attacker Controlled Name",
            "email": "attacker@example.test",
            "tenant_id": "protected-workspace",
            "agent_name": "Attacker Agent",
            "default_language": "en",
            "plan": "starter",
            "seed_starter_data": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "protected-workspace-2"
    assert body["owner_user_id"].startswith("pending-signup-")

    with session_scope() as db:
        protected = db.get(Tenant, "protected-workspace")
        assert protected is not None
        assert protected.name == "Protected Workspace"
        assert protected.agent_name == "Original Agent"
        assert protected.default_language == "hi"
        assert protected.plan == "enterprise"
        protected_members = (
            db.execute(
                select(TenantMember).where(
                    TenantMember.tenant_id == "protected-workspace"
                )
            )
            .scalars()
            .all()
        )
        assert [(member.user_id, member.role) for member in protected_members] == [
            ("protected-owner", ROLE_OWNER)
        ]


def test_anonymous_signup_rejects_caller_controlled_owner_user_id(client):
    response = client.post(
        "/api/auth/signup",
        json={
            "company_name": "Spoofed Owner Ltd",
            "email": "attacker@example.test",
            "user_id": "protected-owner",
            "seed_starter_data": False,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "verified_identity_required_for_user_id"
    with session_scope() as db:
        assert db.get(Tenant, "spoofed-owner-ltd") is None


def test_signup_rejects_unimplemented_language(client):
    response = client.post(
        "/api/auth/signup",
        json={
            "company_name": "Unsupported Language Ltd",
            "email": "owner@example.test",
            "default_language": "es",
        },
    )

    assert response.status_code == 422


def test_turnstile_challenge_rejection_on_signup(monkeypatch, client):
    s = get_settings()
    monkeypatch.setattr(s, "turnstile_secret_key", "test-secret-turnstile", raising=False)

    payload = {
        "company_name": "Shield Security Ltd",
        "email": "ops@shield.co.uk",
        "name": "Alice",
        "default_language": "en",
    }

    # Request without Turnstile token when Turnstile is enabled must fail
    r = client.post("/api/auth/signup", json=payload)
    assert r.status_code == 403
    assert r.json()["detail"] == "turnstile_token_required"


def test_two_independent_signups_have_zero_data_bleed(client):
    # 1. Sign up Tenant A
    r_a = client.post(
        "/api/auth/signup",
        json={
            "company_name": "Alpha Express Ltd",
            "email": "alice@alphaexpress.co.uk",
            "name": "Alice",
            "default_language": "en",
            "seed_starter_data": True,
        },
    )
    assert r_a.status_code == 200
    tenant_a_id = r_a.json()["tenant_id"]

    # 2. Sign up Tenant B
    r_b = client.post(
        "/api/auth/signup",
        json={
            "company_name": "Beta Haulage UK Ltd",
            "email": "bob@betahaulage.co.uk",
            "name": "Bob",
            "default_language": "en",
            "seed_starter_data": True,
        },
    )
    assert r_b.status_code == 200
    tenant_b_id = r_b.json()["tenant_id"]

    assert tenant_a_id != tenant_b_id

    # 3. Check Database isolation
    with session_scope() as db:
        prods_a = db.execute(select(Product).where(Product.tenant_id == tenant_a_id)).scalars().all()
        prods_b = db.execute(select(Product).where(Product.tenant_id == tenant_b_id)).scalars().all()

        assert len(prods_a) == 3
        assert len(prods_b) == 3

        skus_a = {p.sku for p in prods_a}
        skus_b = {p.sku for p in prods_b}

        # SKUs should be partitioned by tenant prefix
        assert skus_a.isdisjoint(skus_b)

        # Memberships should be strictly partitioned
        members_a = db.execute(select(TenantMember).where(TenantMember.tenant_id == tenant_a_id)).scalars().all()
        members_b = db.execute(select(TenantMember).where(TenantMember.tenant_id == tenant_b_id)).scalars().all()

        assert len(members_a) == 1
        assert len(members_b) == 1
        assert members_a[0].subject_email_hash == normalized_email_hash("alice@alphaexpress.co.uk")
        assert members_b[0].subject_email_hash == normalized_email_hash("bob@betahaulage.co.uk")


def test_cli_onboard_tenant_script(monkeypatch):
    import scripts.onboard_tenant as cli_script

    test_args = [
        "onboard_tenant.py",
        "--tenant-id",
        "cli-test-corp",
        "--company-name",
        "CLI Test Logistics Ltd",
        "--phone-number",
        "+447700900999",
        "--admin-email",
        "cli@testcorp.co.uk",
        "--language",
        "en",
        "--seed-data",
    ]

    monkeypatch.setattr("sys.argv", test_args)
    cli_script.main()

    with session_scope() as db:
        tenant = db.get(Tenant, "cli-test-corp")
        assert tenant is not None
        assert tenant.name == "CLI Test Logistics Ltd"
        assert tenant.default_language == "en"

        phone = db.get(TenantPhoneNumber, "+447700900999")
        assert phone is not None
        assert phone.tenant_id == "cli-test-corp"
        assert phone.provider == "connect"

        member = (
            db.execute(select(TenantMember).where(TenantMember.tenant_id == "cli-test-corp"))
            .scalars()
            .first()
        )
        assert member is not None
        assert member.role == ROLE_OWNER
        assert member.status == "active"

