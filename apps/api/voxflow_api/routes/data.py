"""FastAPI routes for CRUD + dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import desc, select

from ..auth import get_auth
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
    session_scope,
)
from ..llm import get_llm
from ..schemas import (
    CallAction,
    CallOut,
    CallTurn,
    OrderCreate,
    OrderItemIn,
    OrderOut,
    ResolutionIn,
    ShipmentOut,
    StockItem,
    SupplierOut,
)


router = APIRouter()


def _tenant_id(request: Request, query_tenant: str | None = None) -> str:
    """Prefer the authenticated tenant; fall back to the query param for compatibility."""
    auth = get_auth(request)
    if auth.tenant_id:
        return auth.tenant_id
    if query_tenant:
        return query_tenant
    return get_settings().default_tenant_id


# ---------- Tenants ----------


@router.get("/tenants")
def list_tenants() -> list[dict[str, Any]]:
    with session_scope() as db:
        rows = db.execute(select(Tenant).where(Tenant.active == 1)).scalars().all()
        return [{"id": t.id, "name": t.name, "logo_url": t.logo_url} for t in rows]


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
def get_supplier(request: Request, supplier_id: str) -> Supplier:
    tenant = _tenant_id(request)
    with session_scope() as db:
        s = db.get(Supplier, supplier_id)
        if not s or s.tenant_id != tenant:
            raise HTTPException(status_code=404, detail="supplier_not_found")
        return s


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
        stmt = select(Stock, Product).join(Product, Product.sku == Stock.sku, isouter=True).where(Stock.tenant_id == tenant)
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
    tenant = _tenant_id(request, tenant_id)
    order_id = f"PO-{int(datetime.now(timezone.utc).timestamp())}-MAN"
    items = [{"sku": i.sku, "quantity": i.quantity} for i in payload.items]
    if not items:
        raise HTTPException(status_code=400, detail="no_items")
    total_qty = sum(i["quantity"] for i in items)
    with session_scope() as db:
        sup = db.get(Supplier, payload.supplier_id)
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
def get_order(request: Request, order_id: str) -> dict[str, Any]:
    tenant = _tenant_id(request)
    with session_scope() as db:
        o = db.get(Order, order_id)
        if not o or o.tenant_id != tenant:
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
    """Return all calls currently in progress (in-memory, not yet persisted).

    Reads the pipeline's live session map — these are calls still connected
    to Twilio or the browser simulator. Calls disappear from this list as
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
def get_call(request: Request, call_id: str) -> dict[str, Any]:
    tenant = _tenant_id(request)
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
    tenant = _tenant_id(request, tenant_id)
    with session_scope() as db:
        c = db.get(Call, call_id)
        if not c or c.tenant_id != tenant:
            raise HTTPException(status_code=404, detail="call_not_found")
        c.staff_resolution = payload.staff_resolution
        c.staff_resolved_at = datetime.now(timezone.utc)
        db.flush()
        return _call_out(c)


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


# ---------- Health ----------


@router.get("/health")
def health() -> dict[str, Any]:
    from ..config import get_settings

    s = get_settings()
    return {
        "ok": True,
        "service": "voxflow-api",
        "version": "0.1.0",
        "llm_provider": s.llm_provider,
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


def _call_out(c: Call) -> dict[str, Any]:
    transcript_raw = json.loads(c.transcript_json or "[]")
    actions_raw = json.loads(c.actions_json or "[]")
    now_ts = (c.started_at or datetime.now(timezone.utc)).timestamp()
    transcript = [
        CallTurn(
            role=t.get("role", "agent"),
            text=t.get("text", ""),
            at=datetime.fromtimestamp(t.get("at", now_ts), tz=timezone.utc),
        )
        for t in transcript_raw
    ]
    actions = [
        CallAction(
            name=a.get("name", ""),
            args=a.get("args", {}),
            result=a.get("result"),
            at=datetime.fromtimestamp(a.get("at", now_ts), tz=timezone.utc),
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
        "sheet_synced": bool(c.sheet_synced),
        "verified": bool(c.verified),
    }
