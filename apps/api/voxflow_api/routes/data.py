"""FastAPI routes for CRUD + dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy import desc, select

from ..auth import (
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    normalized_email_hash,
    require_authenticated_user,
    require_platform_admin,
    require_tenant_role,
)
from ..config import get_settings
from ..db import (
    Appointment,
    Call,
    CommunicationLog,
    Order,
    Product,
    Shipment,
    Stock,
    Supplier,
    Tenant,
    TenantMember,
    TenantPhoneNumber,
    session_scope,
)
from ..llm import get_llm
from ..schemas import (
    AppointmentCreate,
    CallAction,
    CallOut,
    CallTurn,
    CommunicationCreate,
    CsvImportOut,
    CsvValidationOut,
    OrderCreate,
    OrderItemIn,
    OrderOut,
    OutboundCallIn,
    ResolutionIn,
    ShipmentOut,
    StockItem,
    SupplierCreate,
    SupplierOut,
    WorkspaceProvisionIn,
    WorkspaceProvisionOut,
)
from ..services.data_ingestion import (
    ENTITY_SCHEMAS,
    SUPPORTED_ENTITIES,
    get_csv_template,
    ingest_csv_data,
    parse_csv_content,
    validate_csv_data,
)

from ..services.telephony_routing import normalize_e164


router = APIRouter()


def _tenant_id(
    request: Request,
    query_tenant: str | None = None,
    *,
    write: bool = False,
) -> str:
    """Resolve and authorize a tenant without trusting mutable JWT metadata.

    Every data route calls this resolver before reading or writing tenant state.
    The demo receives only the fixed configured demonstration tenant, while real
    users require an active application-owned membership. The compatibility mode
    is restricted to the deterministic offline test configuration.
    """

    tenant_id = (query_tenant or get_settings().default_tenant_id).strip()
    if not tenant_id:
        raise HTTPException(status_code=422, detail="tenant_id_required")
    with session_scope() as authorization_db:
        require_tenant_role(
            request,
            authorization_db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR} if write else {ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=not write,
        )
    return tenant_id


# ---------- Tenants & Workspaces ----------


@router.get("/tenants")
def list_tenants(request: Request) -> list[dict[str, Any]]:
    """Return only workspaces the caller is authorized to access.

    The historical global tenant directory is available only in the explicit
    offline compatibility mode used by legacy deterministic tests. Production
    callers use the tenant-membership ledger, and the demo sees its fixed tenant.
    """

    settings = get_settings()
    with session_scope() as db:
        if not settings.tenant_authorization_enforced:
            rows = db.execute(select(Tenant).where(Tenant.active == 1)).scalars().all()
        else:
            auth = require_authenticated_user(request, allow_demo=True)
            if auth.is_demo:
                tenant = db.get(Tenant, settings.demo_tenant_id)
                rows = [tenant] if tenant and tenant.active else []
            else:
                rows = [
                    tenant
                    for _, tenant in db.execute(
                        select(TenantMember, Tenant)
                        .join(Tenant, Tenant.id == TenantMember.tenant_id)
                        .where(
                            TenantMember.user_id == auth.user_id,
                            TenantMember.status == "active",
                            Tenant.active == 1,
                        )
                    ).all()
                ]
        return [
            {
                "id": tenant.id,
                "name": tenant.name,
                "logo_url": tenant.logo_url,
                "agent_name": tenant.agent_name,
                "plan": tenant.plan,
                "default_language": tenant.default_language,
            }
            for tenant in rows
        ]


@router.post("/workspaces/provision", response_model=WorkspaceProvisionOut)
def provision_workspace(payload: WorkspaceProvisionIn, request: Request) -> WorkspaceProvisionOut:
    """Provision a workspace only from the explicit platform-admin control plane."""

    actor = require_platform_admin(request)
    slug = (
        payload.tenant_id.lower()
        .strip()
        .replace(" ", "-")
        .replace("_", "-")
    )
    if not slug:
        slug = f"tenant-{int(datetime.now(timezone.utc).timestamp())}"

    company_name = payload.name.strip() or "Voice Operations Workspace"
    stats: dict[str, int] = {"products": 0, "suppliers": 0, "stock_units": 0, "orders": 0}

    with session_scope() as db:
        # 1. Create or update tenant row
        tenant = db.get(Tenant, slug)
        if not tenant:
            tenant = Tenant(
                id=slug,
                name=company_name,
                plan=payload.plan or "pro",
                agent_name="Vaani",
                welcome_message=f"Hello, and welcome to {company_name}. How can I help you today?",
                default_language=payload.default_language or "en",
                active=1,
            )
            db.add(tenant)
            db.flush()
            db.add(
                TenantMember(
                    id=f"tm-{slug[:24]}-{int(datetime.now(timezone.utc).timestamp())}",
                    tenant_id=slug,
                    user_id=actor.user_id,
                    subject_email_hash=normalized_email_hash(actor.email, fallback_subject=actor.user_id),
                    role=ROLE_OWNER,
                    status="active",
                    invited_by="platform_admin_workspace_provisioning",
                    activated_at=datetime.now(timezone.utc),
                )
            )
        else:
            tenant.active = 1
            if payload.name:
                tenant.name = company_name
            if payload.plan:
                tenant.plan = payload.plan
            db.flush()

        # 2. Seed starter data if requested and not yet seeded
        if payload.seed_starter_data:
            existing_products = (
                db.execute(select(Product).where(Product.tenant_id == slug))
                .scalars()
                .all()
            )
            if not existing_products:
                prefix = slug.replace("-", "").upper()[:3] or "VOX"
                starter_products = [
                    Product(
                        sku=f"{prefix}-CARTON-100",
                        tenant_id=slug,
                        name="Heavy Duty Shipping Carton (Pack of 100)",
                        category="Packaging",
                        pack_size="100 pcs",
                        mrp_inr=1200.0,
                    ),
                    Product(
                        sku=f"{prefix}-PALLET-STD",
                        tenant_id=slug,
                        name="Standard Euro Wooden Pallet (1200x800mm)",
                        category="Warehouse",
                        pack_size="1 unit",
                        mrp_inr=850.0,
                    ),
                    Product(
                        sku=f"{prefix}-TAPE-ROLL-06",
                        tenant_id=slug,
                        name="Reinforced Packing Tape 3-inch (Pack of 6)",
                        category="Packaging",
                        pack_size="6 rolls",
                        mrp_inr=450.0,
                    ),
                    Product(
                        sku=f"{prefix}-WATER-500ML",
                        tenant_id=slug,
                        name="Packaged Drinking Water 500ml (Pack of 24)",
                        category="Beverages",
                        pack_size="500ml x 24",
                        mrp_inr=240.0,
                    ),
                ]
                for p in starter_products:
                    db.add(p)
                db.flush()
                stats["products"] = len(starter_products)

                # Seed Stock
                stock_entries = [
                    Stock(tenant_id=slug, sku=f"{prefix}-CARTON-100", warehouse="Main Distribution Center", quantity=250),
                    Stock(tenant_id=slug, sku=f"{prefix}-CARTON-100", warehouse="Express Logistics Bay", quantity=80),
                    Stock(tenant_id=slug, sku=f"{prefix}-PALLET-STD", warehouse="Main Distribution Center", quantity=140),
                    Stock(tenant_id=slug, sku=f"{prefix}-TAPE-ROLL-06", warehouse="Main Distribution Center", quantity=300),
                    Stock(tenant_id=slug, sku=f"{prefix}-WATER-500ML", warehouse="Main Distribution Center", quantity=500),
                    Stock(tenant_id=slug, sku=f"{prefix}-WATER-500ML", warehouse="Express Logistics Bay", quantity=180),
                ]
                for s in stock_entries:
                    db.add(s)
                stats["stock_units"] = sum(s.quantity for s in stock_entries)

                # Seed Suppliers / Customer Accounts with PIN auth
                starter_suppliers = [
                    Supplier(
                        id=f"sup-{slug}-001",
                        tenant_id=slug,
                        name="Apex Supply & Freight Corp",
                        phone="+919876543210",
                        city="Gurgaon",
                        state="Haryana",
                        pincode="122001",
                        contact_person=payload.admin_name or "Rajesh Kumar",
                        gstin="06AAAAA0000A1Z5",
                        auth_pin_hash=None,
                        pin_updated_at=None,
                        contact_type="customer",
                        active=1,
                    ),
                    Supplier(
                        id=f"sup-{slug}-002",
                        tenant_id=slug,
                        name="Metro Wholesale Distributors",
                        phone="+919812345678",
                        city="Delhi NCR",
                        state="Delhi",
                        pincode="110001",
                        contact_person="Amit Sharma",
                        gstin="07BBBBB1111B1Z2",
                        auth_pin_hash=None,
                        pin_updated_at=None,
                        contact_type="customer",
                        active=1,
                    ),
                    Supplier(
                        id=f"sup-{slug}-003",
                        tenant_id=slug,
                        name="BlueLine Logistics Partners",
                        phone="+919999888777",
                        city="Noida",
                        state="Uttar Pradesh",
                        pincode="201301",
                        contact_person="Sanjay Verma",
                        gstin="09CCCCC2222C1Z9",
                        auth_pin_hash=None,
                        pin_updated_at=None,
                        contact_type="supplier",
                        active=1,
                    ),
                ]
                for sup in starter_suppliers:
                    db.add(sup)
                db.flush()
                stats["suppliers"] = len(starter_suppliers)

                # Seed Initial Confirmed PO
                po_id = f"PO-{prefix}-001"
                initial_order = Order(
                    id=po_id,
                    tenant_id=slug,
                    supplier_id=f"sup-{slug}-001",
                    status="confirmed",
                    items_json=json.dumps([
                        {"sku": f"{prefix}-CARTON-100", "quantity": 10},
                        {"sku": f"{prefix}-TAPE-ROLL-06", "quantity": 5},
                    ]),
                    total_qty=15,
                    notes="Initial automated onboarding stock order",
                )
                db.add(initial_order)
                db.flush()
                stats["orders"] = 1

                # Seed Starter Shipment
                now = datetime.now(timezone.utc)
                initial_shipment = Shipment(
                    id=f"SHIP-{prefix}-001",
                    tenant_id=slug,
                    order_id=po_id,
                    status="in_transit",
                    carrier="Delhivery Express",
                    tracking_no=f"DLV{prefix}99812",
                    expected_delivery=now + timedelta(days=2),
                    last_update=now,
                    history_json=json.dumps([
                        {
                            "status": "Dispatched from Central Warehouse",
                            "location": "Gurgaon Hub",
                            "timestamp": now.isoformat(),
                        }
                    ]),
                )
                db.add(initial_shipment)

                # Seed Starter Dock Appointment
                initial_appointment = Appointment(
                    id=f"APT-{prefix}-001",
                    tenant_id=slug,
                    supplier_id=f"sup-{slug}-001",
                    datetime=now + timedelta(days=1),
                    purpose="Onboarding Dock Slot & Delivery Inspection",
                    status="confirmed",
                )
                db.add(initial_appointment)

                # Seed Starter Welcome Communication Log
                initial_comm = CommunicationLog(
                    id=f"msg-{slug[:6]}-001",
                    tenant_id=slug,
                    channel="sms",
                    recipient=payload.admin_email or "+919876543210",
                    subject="Welcome to VoxFlow",
                    body=f"Welcome to VoxFlow Voice Operations for {company_name}! Your automated AI voice assistant is live and ready.",
                    status="delivered",
                )
                db.add(initial_comm)

        # 3. Map phone number if provided
        if payload.phone_number:
            try:
                clean_phone = normalize_e164(payload.phone_number)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            existing_phone = db.get(TenantPhoneNumber, clean_phone)
            if existing_phone and existing_phone.tenant_id != slug:
                raise HTTPException(status_code=409, detail="phone_number_owned_by_another_tenant")
            if existing_phone:
                existing_phone.label = f"{company_name} Inbound Line"
                existing_phone.active = 1
            else:
                db.add(
                    TenantPhoneNumber(
                        phone_number=clean_phone,
                        tenant_id=slug,
                        label=f"{company_name} Inbound Line",
                        active=1,
                    )
                )

    return WorkspaceProvisionOut(
        ok=True,
        tenant_id=slug,
        name=company_name,
        plan=payload.plan or "pro",
        message=f"Workspace '{company_name}' ({slug}) was provisioned in simulation-safe mode; no worker, provider, callback, or outbound operation was activated.",
        stats=stats,
    )


# ---------- Dashboard summary ----------


@router.get("/summary")
def summary(request: Request, tenant_id: str | None = Query(default=None)) -> dict[str, Any]:
    """Top-level counters for the dashboard hero."""
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        q_sup = select(Supplier)
        q_ord = select(Order)
        q_call = select(Call)
        q_sup = q_sup.where(Supplier.tenant_id == tenant)
        q_ord = q_ord.where(Order.tenant_id == tenant)
        q_call = q_call.where(Call.tenant_id == tenant)

        total_suppliers = db.execute(q_sup).scalars().all()
        total_orders = db.execute(q_ord).scalars().all()
        total_calls = db.execute(q_call).scalars().all()

        last_call_q = select(Call).where(Call.tenant_id == tenant).order_by(desc(Call.started_at)).limit(1)
        last_call = db.execute(last_call_q).scalar_one_or_none()

    return {
        "suppliers": len(total_suppliers),
        "orders": len(total_orders),
        "calls": len(total_calls),
        "last_call_at": last_call.started_at.isoformat() if last_call else None,
        "pending_orders": sum(1 for o in total_orders if o.status in ("pending", "confirmed")),
    }


# ---------- Suppliers ----------


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    request: Request,
    q: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
) -> list[Supplier]:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        stmt = select(Supplier).where(Supplier.tenant_id == tenant).order_by(Supplier.name)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(Supplier.name.ilike(like) | Supplier.phone.ilike(like) | Supplier.city.ilike(like))
        return db.execute(stmt).scalars().all()


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    request: Request,
    supplier_id: str,
    tenant_id: str | None = Query(default=None),
) -> Supplier:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        s = db.execute(
            select(Supplier).where(
                Supplier.tenant_id == tenant,
                Supplier.id == supplier_id,
            )
        ).scalars().first()
        if not s:
            raise HTTPException(status_code=404, detail="supplier_not_found")
        return s


@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(
    request: Request,
    payload: SupplierCreate,
    tenant_id: str | None = Query(default=None),
) -> dict[str, Any]:
    tenant = _tenant_id(request, tenant_id, write=True)
    try:
        clean_phone = normalize_e164(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    sup_id = f"sup-{tenant}-{int(datetime.now(timezone.utc).timestamp()) % 100000}"
    with session_scope() as db:
        s = Supplier(
            id=sup_id,
            tenant_id=tenant,
            name=payload.name.strip(),
            phone=clean_phone,
            city=payload.city.strip(),
            state=payload.state.strip(),
            pincode=payload.pincode.strip(),
            contact_person=payload.contact_person.strip(),
            gstin=payload.gstin.strip().upper(),
            auth_pin=None,
            auth_pin_hash=None,
            contact_type="supplier",
            active=1,
        )
        db.add(s)
        db.flush()
        return {
            "id": s.id,
            "name": s.name,
            "phone": s.phone,
            "city": s.city,
            "state": s.state,
            "pincode": s.pincode,
            "contact_person": s.contact_person,
            "gstin": s.gstin,
            "contact_type": s.contact_type,
            "pin_configured": False,
        }


# ---------- Products / Stock ----------


@router.get("/stock", response_model=list[StockItem])
def list_stock(
    request: Request,
    sku: str | None = None,
    warehouse: str | None = None,
    tenant_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        stmt = (
            select(Stock, Product)
            .join(
                Product,
                (Product.sku == Stock.sku) & (Product.tenant_id == Stock.tenant_id),
                isouter=True,
            )
            .where(Stock.tenant_id == tenant)
        )
        if sku:
            stmt = stmt.where(Stock.sku == sku)
        if warehouse:
            stmt = stmt.where(Stock.warehouse == warehouse)
        rows = db.execute(stmt).all()
        return [
            {
                "sku": s.sku,
                "name": p.name if p else "",
                "warehouse": s.warehouse,
                "quantity": s.quantity,
                "pack_size": p.pack_size if p else "",
                "mrp_inr": p.mrp_inr if p else 0.0,
            }
            for s, p in rows
        ]


# ---------- Orders ----------


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    request: Request,
    supplier_id: str | None = None,
    status: str | None = None,
    tenant_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        stmt = select(Order).where(Order.tenant_id == tenant).order_by(desc(Order.created_at))
        if supplier_id:
            stmt = stmt.where(Order.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(Order.status == status)
        rows = db.execute(stmt).scalars().all()
        return [_order_out(o) for o in rows]


@router.post("/orders", response_model=OrderOut)
def create_order(request: Request, payload: OrderCreate, tenant_id: str | None = Query(default=None)) -> dict[str, Any]:
    tenant = _tenant_id(request, tenant_id, write=True)
    order_id = f"PO-{int(datetime.now(timezone.utc).timestamp())}-MAN"
    items = [{"sku": i.sku, "quantity": i.quantity} for i in payload.items]
    if not items:
        raise HTTPException(status_code=400, detail="no_items")
    total_qty = sum(i["quantity"] for i in items)
    with session_scope() as db:
        sup = db.execute(
            select(Supplier).where(
                Supplier.tenant_id == tenant,
                Supplier.id == payload.supplier_id,
            )
        ).scalars().first()
        if not sup:
            raise HTTPException(status_code=404, detail="supplier_not_found")
        o = Order(
            id=order_id,
            tenant_id=tenant,
            supplier_id=payload.supplier_id,
            status="pending",
            items_json=json.dumps(items),
            total_qty=total_qty,
            notes=payload.notes,
        )
        db.add(o)
        db.flush()
        return _order_out(o)


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    request: Request,
    order_id: str,
    tenant_id: str | None = Query(default=None),
) -> dict[str, Any]:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        o = db.execute(
            select(Order).where(
                Order.tenant_id == tenant,
                Order.id == order_id,
            )
        ).scalars().first()
        if not o:
            raise HTTPException(status_code=404, detail="order_not_found")
        return _order_out(o)


# ---------- Shipments ----------


@router.get("/shipments", response_model=list[ShipmentOut])
def list_shipments(
    request: Request,
    order_id: str | None = None,
    tenant_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        stmt = select(Shipment).where(Shipment.tenant_id == tenant).order_by(desc(Shipment.last_update))
        if order_id:
            stmt = stmt.where(Shipment.order_id == order_id)
        rows = db.execute(stmt).scalars().all()
        return [
            {
                "id": s.id,
                "order_id": s.order_id,
                "status": s.status,
                "carrier": s.carrier,
                "tracking_no": s.tracking_no,
                "expected_delivery": s.expected_delivery,
                "last_update": s.last_update,
                "history": json.loads(s.history_json or "[]"),
            }
            for s in rows
        ]


# ---------- Active (in-progress) Calls — Day 16 ----------


@router.get("/active-calls")
def list_active_calls(
    request: Request,
    tenant_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    """Active in-memory calls — live right now, receiving audio frames
    to Amazon Connect or the browser simulator. Calls disappear from this list as
    soon as they end and are persisted to the database.
    """
    import time
    tenant = _tenant_id(request, tenant_id)

    # Import lazily to avoid circular import at module load time.
    from .ws import get_pipeline
    pipeline = get_pipeline()

    now = time.time()
    result = []
    for session in list(pipeline._sessions.values()):
        if session.tenant_id != tenant:
            continue
        result.append({
            "call_id": session.call_id,
            "tenant_id": session.tenant_id,
            "caller_phone": session.caller_phone or "",
            "caller_name": session.caller_name or "",
            "company_name": session.company_name or "",
            "intent": session.intent or "",
            "verified": session.verified,
            "pin_verified": session.pin_verified,
            "outcome": session.outcome,
            "turn_count": len([t for t in session.transcript if t.role == "agent"]),
            "elapsed_sec": round(now - session.started_at),
            "started_at": session.started_at,
        })

    # Sort by start time, oldest first
    result.sort(key=lambda x: x["started_at"])
    return result


# ---------- Calls ----------


@router.get("/calls", response_model=list[CallOut])
def list_calls(
    request: Request,
    limit: int = 50,
    tenant_id: str | None = Query(default=None),
    escalated: bool | None = Query(default=None),
    resolution_status: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        stmt = select(Call).where(Call.tenant_id == tenant).order_by(desc(Call.started_at)).limit(limit)
        if escalated is not None:
            stmt = stmt.where(Call.escalated == (1 if escalated else 0))
        if resolution_status is not None:
            stmt = stmt.where(Call.resolution_status == resolution_status)
        rows = db.execute(stmt).scalars().all()
        return [_call_out(c) for c in rows]


@router.get("/calls/{call_id}", response_model=CallOut)
def get_call(
    request: Request,
    call_id: str,
    tenant_id: str | None = Query(default=None),
) -> dict[str, Any]:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        c = db.get(Call, call_id)
        if not c or c.tenant_id != tenant:
            raise HTTPException(status_code=404, detail="call_not_found")
        return _call_out(c)


@router.patch("/calls/{call_id}/resolution", response_model=CallOut)
def patch_call_resolution(
    request: Request,
    call_id: str,
    payload: ResolutionIn,
    tenant_id: str | None = Query(default=None),
) -> dict[str, Any]:
    tenant = _tenant_id(request, tenant_id, write=True)
    with session_scope() as db:
        c = db.get(Call, call_id)
        if not c or c.tenant_id != tenant:
            raise HTTPException(status_code=404, detail="call_not_found")
        c.staff_resolution = payload.staff_resolution
        c.staff_resolved_at = datetime.now(timezone.utc)
        db.flush()
        return _call_out(c)


@router.get("/calls/{call_id}/recording")
def get_call_recording_link(
    request: Request,
    call_id: str,
    tenant_id: str | None = Query(default=None),
) -> dict[str, Any]:
    """Report recording availability without exposing a provider URL."""

    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        call = db.get(Call, call_id)
        if not call or call.tenant_id != tenant:
            raise HTTPException(status_code=404, detail="call_not_found")
        return {
            "call_id": call_id,
            "recording_available": bool(call.recording_url),
            "retrieval_enabled": False,
            "reason": "recording_retrieval_disabled_by_safety_posture",
        }


@router.get("/calls/{call_id}/recording/download")
async def download_call_recording(
    request: Request,
    call_id: str,
    tenant_id: str | None = Query(default=None),
):
    """Reject browser-triggered provider recording retrieval in the MVP posture."""

    _tenant_id(request, tenant_id)
    raise HTTPException(status_code=409, detail="recording_retrieval_disabled_by_safety_posture")


@router.post("/calls/outbound")
async def trigger_outbound_call(
    request: Request,
    payload: OutboundCallIn,
    tenant_id: str | None = Query(default=None),
) -> dict[str, Any]:
    """Hard-disable legacy direct provider dispatch in the free-tier MVP.

    This explicit safe failure prevents a browser request from reaching Dial or
    any other telephony provider. Future controlled-pilot dispatch remains gated
    through the durable policy path, explicit human authorization, and separate
    provider configuration; none of those controls are enabled by this release.
    """

    _tenant_id(request, tenant_id, write=True)
    raise HTTPException(status_code=409, detail="outbound_calls_disabled_by_safety_posture")


# ---------- Appointments ----------


@router.get("/appointments")
def list_appointments(request: Request, tenant_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        stmt = select(Appointment).where(Appointment.tenant_id == tenant).order_by(desc(Appointment.datetime))
        rows = db.execute(stmt).scalars().all()
        return [
            {
                "id": a.id,
                "tenant_id": a.tenant_id,
                "supplier_id": a.supplier_id,
                "datetime": a.datetime.isoformat(),
                "purpose": a.purpose,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in rows
        ]


@router.post("/appointments")
def create_appointment(
    request: Request,
    payload: AppointmentCreate,
    tenant_id: str | None = Query(default=None),
) -> dict[str, Any]:
    tenant = _tenant_id(request, tenant_id, write=True)
    app_id = f"app-{tenant}-{int(datetime.now(timezone.utc).timestamp()) % 100000}"
    try:
        dt = datetime.fromisoformat(payload.datetime.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)

    with session_scope() as db:
        app = Appointment(
            id=app_id,
            tenant_id=tenant,
            supplier_id=payload.supplier_id or "",
            datetime=dt,
            purpose=payload.purpose or "Supplier Operations & Delivery Audit",
            status="confirmed",
        )
        db.add(app)
        db.flush()
        return {
            "id": app.id,
            "tenant_id": app.tenant_id,
            "supplier_id": app.supplier_id,
            "datetime": app.datetime.isoformat(),
            "purpose": app.purpose,
            "status": app.status,
            "created_at": app.created_at.isoformat(),
        }


# ---------- Communications Log ----------


@router.get("/communications")
def list_communications(request: Request, tenant_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        stmt = select(CommunicationLog).where(CommunicationLog.tenant_id == tenant).order_by(desc(CommunicationLog.timestamp))
        rows = db.execute(stmt).scalars().all()
        return [
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "channel": c.channel,
                "recipient": c.recipient,
                "subject": c.subject,
                "body": c.body,
                "status": c.status,
                "timestamp": c.timestamp.isoformat(),
            }
            for c in rows
        ]


@router.post("/communications")
def create_communication(
    request: Request,
    payload: CommunicationCreate,
    tenant_id: str | None = Query(default=None),
) -> dict[str, Any]:
    tenant = _tenant_id(request, tenant_id, write=True)
    comm_id = f"msg-{int(datetime.now(timezone.utc).timestamp()) % 1000000}"
    with session_scope() as db:
        comm = CommunicationLog(
            id=comm_id,
            tenant_id=tenant,
            channel=payload.channel,
            recipient=payload.recipient.strip(),
            subject=payload.subject or "",
            body=payload.body.strip(),
            status="delivered",
        )
        db.add(comm)
        db.flush()
        return {
            "id": comm.id,
            "tenant_id": comm.tenant_id,
            "channel": comm.channel,
            "recipient": comm.recipient,
            "subject": comm.subject,
            "body": comm.body,
            "status": comm.status,
            "timestamp": comm.timestamp.isoformat(),
        }


# ---------- Health ----------


@router.api_route("/health", methods=["GET", "HEAD"])
def health() -> dict[str, Any]:
    from ..config import get_settings

    s = get_settings()
    return {
        "ok": True,
        "service": "voxflow-api",
        "version": "0.1.0",
        "llm_provider": s.llm_provider,
        "db_schema_bootstrap_mode": s.db_schema_bootstrap_mode,
    }


@router.get("/health/llm")
async def llm_health() -> dict[str, Any]:
    try:
        ok = await get_llm().health()
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": ok}


# ---------- Helpers ----------


def _order_out(o: Order) -> dict[str, Any]:
    items_raw = json.loads(o.items_json or "[]")
    items = [OrderItemIn(sku=i["sku"], quantity=i["quantity"]) for i in items_raw]
    return {
        "id": o.id,
        "supplier_id": o.supplier_id,
        "status": o.status,
        "items": items,
        "total_qty": o.total_qty,
        "notes": o.notes,
        "created_at": o.created_at,
        "updated_at": o.updated_at,
    }


def _parse_ts(val: Any, fallback_ts: float) -> datetime:
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.fromtimestamp(fallback_ts, tz=timezone.utc)


def _call_out(c: Call) -> dict[str, Any]:
    transcript_raw = json.loads(c.transcript_json or "[]")
    actions_raw = json.loads(c.actions_json or "[]")
    now_ts = (c.started_at or datetime.now(timezone.utc)).timestamp()
    transcript = [
        CallTurn(
            role=t.get("role", "agent"),
            text=t.get("text", ""),
            at=_parse_ts(t.get("at"), now_ts),
        )
        for t in transcript_raw
    ]
    actions = [
        CallAction(
            name=a.get("name", ""),
            args=a.get("args", {}),
            result=a.get("result"),
            at=_parse_ts(a.get("at"), now_ts),
        )
        for a in actions_raw
    ]
    return {
        "id": c.id,
        "started_at": c.started_at,
        "ended_at": c.ended_at,
        "duration_sec": c.duration_sec,
        "supplier_id": c.supplier_id,
        "caller_phone": c.caller_phone,
        "caller_name": c.caller_name,
        "language": c.language,
        "intent": c.intent,
        "outcome": c.outcome,
        "escalated": bool(c.escalated),
        "transcript": transcript,
        "actions": actions,
        "reason": c.reason or "",
        "solution": c.solution or "",
        "resolution_status": c.resolution_status or "",
        "satisfaction": c.satisfaction or "",
        "follow_up_required": bool(c.follow_up_required),
        "staff_resolution": c.staff_resolution or "",
        "staff_resolved_at": c.staff_resolved_at,
        "escalation_priority": c.escalation_priority or "medium",
        "escalation_status": c.escalation_status or "none",
        "assigned_to_user_id": c.assigned_to_user_id,
        "assigned_at": c.assigned_at,
        "sla_due_at": c.sla_due_at,
        "resolved_by_user_id": c.resolved_by_user_id,
        "resolution_category": c.resolution_category,
        "sheet_synced": bool(c.sheet_synced),
        "verified": bool(c.verified),
        "recording_url": c.recording_url,
    }


# ---------- Company Data Ingestion (CSV Import & Templates) ----------


@router.get("/data/entities")
def get_importable_entities() -> dict[str, Any]:
    """Return catalog of entities supported for CSV bulk ingestion."""
    return {
        "entities": [
            {
                "id": k,
                "description": v["description"],
                "required_columns": v["required_columns"],
                "optional_columns": v["optional_columns"],
                "sample_rows": v.get("sample_rows", []),
            }
            for k, v in ENTITY_SCHEMAS.items()
        ]
    }


@router.get("/data/templates/{entity}")
def download_csv_template(entity: str) -> Response:
    """Download standard CSV template for an entity."""
    entity_key = entity.lower().strip()
    if entity_key not in ENTITY_SCHEMAS:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported entity '{entity}'. Allowed: {', '.join(SUPPORTED_ENTITIES)}",
        )
    csv_content = get_csv_template(entity_key)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{entity_key}_template.csv"',
            "Cache-Control": "no-cache",
        },
    )


@router.post("/data/{entity}/validate", response_model=CsvValidationOut)
async def validate_csv(
    entity: str,
    request: Request,
    tenant_id: str | None = Query(None),
) -> CsvValidationOut:
    """Dry-run validation of CSV data before committing to the database."""
    entity_key = entity.lower().strip()
    if entity_key not in ENTITY_SCHEMAS:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported entity '{entity}'. Allowed: {', '.join(SUPPORTED_ENTITIES)}",
        )

    content = ""
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        uploaded = form.get("file")
        if uploaded is not None and hasattr(uploaded, "read"):
            file_bytes = await uploaded.read()
            content = file_bytes.decode("utf-8", errors="replace")
        elif "csv_text" in form:
            content = str(form.get("csv_text") or "")
    elif "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                content = str(body.get("csv_text") or "")
                if not tenant_id and "tenant_id" in body:
                    tenant_id = str(body["tenant_id"])
        except Exception:
            pass
    else:
        raw_body = await request.body()
        content = raw_body.decode("utf-8", errors="replace")

    if not content.strip():
        raise HTTPException(status_code=400, detail="csv_content_required")

    resolved_tenant = _tenant_id(request, tenant_id) if tenant_id else ""
    res = validate_csv_data(entity=entity_key, csv_text=content, tenant_id=resolved_tenant)
    return CsvValidationOut(
        entity=res.entity,
        total_rows=res.total_rows,
        valid_rows=res.valid_rows,
        error_count=res.error_count,
        errors=res.errors,
        preview=res.preview,
        headers=res.headers,
        is_valid=res.is_valid,
    )


@router.post("/data/{entity}/import", response_model=CsvImportOut)
async def import_csv(
    entity: str,
    request: Request,
    tenant_id: str | None = Query(None),
) -> CsvImportOut:
    """Execute transactional bulk CSV import for the authenticated tenant."""
    entity_key = entity.lower().strip()
    if entity_key not in ENTITY_SCHEMAS:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported entity '{entity}'. Allowed: {', '.join(SUPPORTED_ENTITIES)}",
        )

    resolved_tenant = _tenant_id(request, tenant_id, write=True)

    content = ""
    mode = "upsert"
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        uploaded = form.get("file")
        if uploaded is not None and hasattr(uploaded, "read"):
            file_bytes = await uploaded.read()
            content = file_bytes.decode("utf-8", errors="replace")
        elif "csv_text" in form:
            content = str(form.get("csv_text") or "")
        mode = str(form.get("mode") or "upsert")
    elif "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                content = str(body.get("csv_text") or "")
                mode = str(body.get("mode") or "upsert")
        except Exception:
            pass
    else:
        raw_body = await request.body()
        content = raw_body.decode("utf-8", errors="replace")

    if not content.strip():
        raise HTTPException(status_code=400, detail="csv_content_required")

    if entity_key == "suppliers":
        _, supplier_rows = parse_csv_content(content)
        if any(row.get("auth_pin", "").strip() for row in supplier_rows):
            with session_scope() as authorization_db:
                require_tenant_role(
                    request,
                    authorization_db,
                    tenant_id=resolved_tenant,
                    allowed_roles={ROLE_OWNER},
                )

    with session_scope() as db:
        res = ingest_csv_data(
            db=db,
            entity=entity_key,
            csv_text=content,
            tenant_id=resolved_tenant,
            mode=mode,
        )

    if not res.success and res.errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": res.message,
                "errors": res.errors,
                "total_processed": res.total_processed,
            },
        )

    return CsvImportOut(
        success=res.success,
        entity=res.entity,
        tenant_id=res.tenant_id,
        inserted=res.inserted,
        updated=res.updated,
        total_processed=res.total_processed,
        message=res.message,
        errors=res.errors,
    )

