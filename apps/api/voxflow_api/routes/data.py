"""FastAPI routes for CRUD + dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

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
    WorksheetLog,
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
    ShipmentOut,
    StockItem,
    SupplierOut,
)


router = APIRouter()


# ---------- Tenants ----------


@router.get("/tenants")
def list_tenants() -> list[dict[str, Any]]:
    with session_scope() as db:
        rows = db.execute(select(Tenant).where(Tenant.active == 1)).scalars().all()
        return [{"id": t.id, "name": t.name, "logo_url": t.logo_url} for t in rows]


# ---------- Dashboard summary ----------


@router.get("/summary")
def summary(tenant_id: str | None = Query(default=None)) -> dict[str, Any]:
    """Top-level counters for the dashboard hero."""
    with session_scope() as db:
        q_sup = select(Supplier)
        q_ord = select(Order)
        q_call = select(Call)
        if tenant_id:
            q_sup = q_sup.where(Supplier.tenant_id == tenant_id)
            q_ord = q_ord.where(Order.tenant_id == tenant_id)
            q_call = q_call.where(Call.tenant_id == tenant_id)

        total_suppliers = db.execute(q_sup).scalars().all()
        total_orders = db.execute(q_ord).scalars().all()
        total_calls = db.execute(q_call).scalars().all()

        last_call_q = select(Call)
        if tenant_id:
            last_call_q = last_call_q.where(Call.tenant_id == tenant_id)
        last_call = db.execute(last_call_q.order_by(desc(Call.started_at)).limit(1)).scalar_one_or_none()

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
    q: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
) -> list[Supplier]:
    with session_scope() as db:
        stmt = select(Supplier).order_by(Supplier.name)
        if tenant_id:
            stmt = stmt.where(Supplier.tenant_id == tenant_id)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(Supplier.name.ilike(like) | Supplier.phone.ilike(like) | Supplier.city.ilike(like))
        return db.execute(stmt).scalars().all()


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: str) -> Supplier:
    with session_scope() as db:
        s = db.get(Supplier, supplier_id)
        if not s:
            raise HTTPException(status_code=404, detail="supplier_not_found")
        return s


# ---------- Products / Stock ----------


@router.get("/stock", response_model=list[StockItem])
def list_stock(
    sku: str | None = None,
    warehouse: str | None = None,
    tenant_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    with session_scope() as db:
        stmt = select(Stock, Product).join(Product, Product.sku == Stock.sku, isouter=True)
        if tenant_id:
            stmt = stmt.where(Stock.tenant_id == tenant_id)
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
    supplier_id: str | None = None,
    status: str | None = None,
    tenant_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    with session_scope() as db:
        stmt = select(Order).order_by(desc(Order.created_at))
        if tenant_id:
            stmt = stmt.where(Order.tenant_id == tenant_id)
        if supplier_id:
            stmt = stmt.where(Order.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(Order.status == status)
        rows = db.execute(stmt).scalars().all()
        return [_order_out(o) for o in rows]


@router.post("/orders", response_model=OrderOut)
def create_order(payload: OrderCreate, tenant_id: str | None = Query(default="varun")) -> dict[str, Any]:
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
            tenant_id=tenant_id or sup.tenant_id,
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
def get_order(order_id: str) -> dict[str, Any]:
    with session_scope() as db:
        o = db.get(Order, order_id)
        if not o:
            raise HTTPException(status_code=404, detail="order_not_found")
        return _order_out(o)


# ---------- Shipments ----------


@router.get("/shipments", response_model=list[ShipmentOut])
def list_shipments(
    order_id: str | None = None,
    tenant_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    with session_scope() as db:
        stmt = select(Shipment).order_by(desc(Shipment.last_update))
        if tenant_id:
            stmt = stmt.where(Shipment.tenant_id == tenant_id)
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


# ---------- Calls ----------


@router.get("/calls", response_model=list[CallOut])
def list_calls(
    limit: int = 50,
    tenant_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    with session_scope() as db:
        stmt = select(Call).order_by(desc(Call.started_at)).limit(limit)
        if tenant_id:
            stmt = stmt.where(Call.tenant_id == tenant_id)
        rows = db.execute(stmt).scalars().all()
        return [_call_out(c) for c in rows]


@router.get("/calls/{call_id}", response_model=CallOut)
def get_call(call_id: str) -> dict[str, Any]:
    with session_scope() as db:
        c = db.get(Call, call_id)
        if not c:
            raise HTTPException(status_code=404, detail="call_not_found")
        return _call_out(c)


# ---------- Appointments ----------


@router.get("/appointments")
def list_appointments(tenant_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    with session_scope() as db:
        stmt = select(Appointment).order_by(desc(Appointment.datetime))
        if tenant_id:
            stmt = stmt.where(Appointment.tenant_id == tenant_id)
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
def list_communications(tenant_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    with session_scope() as db:
        stmt = select(CommunicationLog).order_by(desc(CommunicationLog.timestamp))
        if tenant_id:
            stmt = stmt.where(CommunicationLog.tenant_id == tenant_id)
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
    }
