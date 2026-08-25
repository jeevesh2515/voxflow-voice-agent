"""Centralized Tenant Provisioning Service for VoxFlow SaaS.

Used by:
1. Self-serve web signup endpoint (/api/auth/signup).
2. Platform-admin workspace provisioning (/api/data/workspaces/provision).
3. Automated CLI onboarding script (scripts/onboard_tenant.py).
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import ROLE_OWNER, normalized_email_hash
from ..db import (
    Order,
    Product,
    Shipment,
    Stock,
    Supplier,
    Tenant,
    TenantMember,
    TenantPhoneNumber,
)
from ..logging import get_logger

log = get_logger(__name__)


def sanitize_slug(name: str) -> str:
    """Convert any business or workspace name into a clean URL-safe slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s_-]", "", name.strip())
    slug = re.sub(r"[\s_]+", "-", cleaned).lower().strip("-")
    return slug or "workspace"


def generate_unique_tenant_slug(db: Session, base_name: str) -> str:
    """Generate a unique URL-safe slug for a tenant without collisions."""
    base_slug = sanitize_slug(base_name)
    slug = base_slug
    counter = 1

    while db.get(Tenant, slug) is not None:
        counter += 1
        if counter <= 50:
            slug = f"{base_slug}-{counter}"
        else:
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
            break

    return slug


def provision_tenant(
    db: Session,
    *,
    name: str,
    owner_user_id: str,
    tenant_id: str | None = None,
    owner_email: str | None = None,
    agent_name: str = "Vaani",
    default_language: str = "en",
    plan: str = "pro",
    phone_number: str | None = None,
    phone_label: str | None = None,
    seed_starter_data: bool = False,
    system_prompt_override: str | None = None,
    welcome_message: str | None = None,
    webhook_url: str | None = None,
    webhook_secret: str | None = None,
    active: int = 1,
    invited_by: str = "self_serve_signup",
) -> dict[str, Any]:
    """Provision a complete, isolated tenant workspace and owner membership."""
    company_name = name.strip() or "Voice Operations Workspace"

    # 1. Resolve slug
    if tenant_id and tenant_id.strip():
        slug = sanitize_slug(tenant_id)
    else:
        slug = generate_unique_tenant_slug(db, company_name)

    now = datetime.now(timezone.utc)

    # 2. Create or update Tenant record
    tenant = db.get(Tenant, slug)
    if not tenant:
        tenant = Tenant(
            id=slug,
            name=company_name,
            agent_name=agent_name or "Vaani",
            default_language=default_language or "en",
            plan=plan or "pro",
            active=active,
            system_prompt_override=system_prompt_override or None,
            welcome_message=welcome_message or f"Hello, and welcome to {company_name}. How can I help you today?",
            webhook_url=webhook_url or None,
            webhook_secret=webhook_secret or None,
            created_at=now,
        )
        db.add(tenant)
        db.flush()
        log.info("provisioning.tenant_created", tenant_id=slug, name=company_name, plan=plan)
    else:
        tenant.active = active
        if name:
            tenant.name = company_name
        if agent_name:
            tenant.agent_name = agent_name
        if default_language:
            tenant.default_language = default_language
        if plan:
            tenant.plan = plan
        if system_prompt_override:
            tenant.system_prompt_override = system_prompt_override
        if welcome_message:
            tenant.welcome_message = welcome_message
        if webhook_url:
            tenant.webhook_url = webhook_url
        if webhook_secret:
            tenant.webhook_secret = webhook_secret
        db.flush()
        log.info("provisioning.tenant_updated", tenant_id=slug, name=company_name)

    # 3. Create or ensure Owner TenantMember record
    email_hash = normalized_email_hash(owner_email, fallback_subject=owner_user_id)
    existing_member = (
        db.execute(
            select(TenantMember).where(
                TenantMember.tenant_id == slug,
                (TenantMember.user_id == owner_user_id)
                | (TenantMember.subject_email_hash == email_hash),
            )
        )
        .scalars()
        .first()
    )

    if not existing_member:
        owner_member = TenantMember(
            id=f"tm-{slug[:24]}-{uuid.uuid4().hex[:12]}",
            tenant_id=slug,
            user_id=owner_user_id,
            subject_email_hash=email_hash,
            role=ROLE_OWNER,
            status="active",
            invited_by=invited_by,
            activated_at=now,
        )
        db.add(owner_member)
        db.flush()
        log.info("provisioning.owner_membership_created", tenant_id=slug, user_id=owner_user_id)
    elif existing_member.status != "active":
        existing_member.status = "active"
        existing_member.role = ROLE_OWNER
        existing_member.user_id = owner_user_id
        db.flush()

    # 4. Optional Phone Number Mapping
    clean_phone: str | None = None
    if phone_number and phone_number.strip():
        clean_phone = phone_number.strip().replace(" ", "")
        phone_entry = db.get(TenantPhoneNumber, clean_phone)
        if phone_entry:
            phone_entry.tenant_id = slug
            phone_entry.label = phone_label or f"{company_name} Main Line"
        else:
            phone_entry = TenantPhoneNumber(
                phone_number=clean_phone,
                tenant_id=slug,
                label=phone_label or f"{company_name} Main Line",
            )
            db.add(phone_entry)
        db.flush()
        log.info("provisioning.phone_mapped", tenant_id=slug, phone_number=clean_phone)

    # 5. Optional Starter Data Seeding
    stats = {"products": 0, "suppliers": 0, "stock_units": 0, "orders": 0}
    seeded = False

    if seed_starter_data:
        existing_products = (
            db.execute(select(Product).where(Product.tenant_id == slug))
            .scalars()
            .all()
        )
        if not existing_products:
            import json

            clean_id = re.sub(r"[^A-Z0-9]", "", slug.upper()) or "VOX"
            if len(clean_id) > 16:
                clean_id = f"{clean_id[:10]}_{clean_id[-5:]}"
            prefix = clean_id
            starter_products = [
                Product(
                    sku=f"{prefix}-CARTON-100",
                    tenant_id=slug,
                    name="Heavy Duty Shipping Carton (Pack of 100)",
                    category="Packaging",
                    pack_size="Pack of 100",
                    mrp_inr=1200.0,
                ),
                Product(
                    sku=f"{prefix}-TAPE-PREMIUM",
                    tenant_id=slug,
                    name="Reinforced Kraft Packaging Tape (72mm)",
                    category="Packaging",
                    pack_size="Pack of 6",
                    mrp_inr=450.0,
                ),
                Product(
                    sku=f"{prefix}-PALLET-STD",
                    tenant_id=slug,
                    name="Standard Heat-Treated Wooden Pallet",
                    category="Logistics",
                    pack_size="1 unit",
                    mrp_inr=850.0,
                ),
            ]
            db.add_all(starter_products)
            db.flush()
            stats["products"] = len(starter_products)

            starter_supplier = Supplier(
                id=f"sup-{slug[:50]}-01",
                tenant_id=slug,
                name=f"{company_name} Primary Supply Depot",
                contact_person="Operations Team",
                phone=clean_phone or "+447700900123",
                city="London",
                state="Greater London",
                pincode="EC1A 1BB",
                contact_type="supplier",
                auth_pin="1234",
                active=1,
            )
            db.add(starter_supplier)
            db.flush()
            stats["suppliers"] = 1

            stock_items = [
                Stock(
                    sku=f"{prefix}-CARTON-100",
                    warehouse="Main Distribution Hub",
                    tenant_id=slug,
                    quantity=45,
                ),
                Stock(
                    sku=f"{prefix}-TAPE-PREMIUM",
                    warehouse="Main Distribution Hub",
                    tenant_id=slug,
                    quantity=120,
                ),
                Stock(
                    sku=f"{prefix}-PALLET-STD",
                    warehouse="Main Distribution Hub",
                    tenant_id=slug,
                    quantity=25,
                ),
            ]
            db.add_all(stock_items)
            db.flush()
            stats["stock_units"] = sum(s.quantity for s in stock_items)

            # Sample starter order
            starter_order = Order(
                id=f"PO-{prefix}-1001",
                tenant_id=slug,
                supplier_id=starter_supplier.id,
                status="confirmed",
                total_qty=30,
                customer_po_ref=f"CUST-{prefix}-901",
                po_signed=1,
                items_json=json.dumps([
                    {
                        "sku": f"{prefix}-CARTON-100",
                        "quantity": 10,
                        "unit_price": 45.00,
                        "description": "Heavy Duty Shipping Carton",
                    },
                    {
                        "sku": f"{prefix}-TAPE-PREMIUM",
                        "quantity": 20,
                        "unit_price": 40.00,
                        "description": "Reinforced Packaging Tape",
                    },
                ]),
                notes="Initial starter catalog seed order",
            )
            db.add(starter_order)
            db.flush()
            stats["orders"] = 1

            # Sample tracking shipment
            starter_shipment = Shipment(
                id=f"shp-{slug[:50]}-1001",
                tenant_id=slug,
                order_id=starter_order.id,
                status="in_transit",
                carrier="Royal Mail Express",
                tracking_no=f"RM{prefix}987654GB",
                expected_delivery=now,
                last_update=now,
                history_json=json.dumps([
                    {"status": "dispatched", "location": "Distribution Centre", "at": now.isoformat()},
                    {"status": "in_transit", "location": "Sorting Hub", "at": now.isoformat()},
                ]),
            )
            db.add(starter_shipment)
            db.flush()
            seeded = True
            log.info("provisioning.starter_data_seeded", tenant_id=slug, stats=stats)

    return {
        "ok": True,
        "tenant_id": slug,
        "name": tenant.name,
        "agent_name": tenant.agent_name,
        "default_language": tenant.default_language,
        "plan": tenant.plan,
        "owner_user_id": owner_user_id,
        "owner_membership_created": True,
        "phone_number": clean_phone,
        "starter_data_seeded": seeded,
        "stats": stats,
    }
