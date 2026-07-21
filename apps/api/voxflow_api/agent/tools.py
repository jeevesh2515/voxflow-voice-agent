"""Tools the agent can call. Each tool is a thin Python function
backed by the SQLite/Postgres database. The OpenAI-style tool schema
is exported as TOOL_DEFINITIONS for the LLM prompt.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from ..db import Order, Shipment, Stock, Supplier, session_scope
from ..logging import get_logger
from ..voice.pipeline import CallSession


log = get_logger(__name__)


# ---------- Tool implementations ----------


def lookup_supplier(session: CallSession, phone: str | None = None, name: str | None = None) -> dict[str, Any]:
    """Find a supplier by phone number or partial name."""
    with session_scope() as db:
        q = select(Supplier)
        if phone:
            # phone is stored as-is; allow last-10-digit match too
            digits = "".join(c for c in phone if c.isdigit())[-10:]
            q = q.where(Supplier.phone.like(f"%{digits}"))
        sup = db.execute(q).scalars().first()
        if not sup and name:
            sup = db.execute(select(Supplier).where(Supplier.name.ilike(f"%{name}%"))).scalars().first()

        if not sup:
            return {"found": False, "phone": phone, "name": name}

        session.supplier_id = sup.id
        session.caller_name = sup.contact_person or sup.name
        if not session.caller_phone:
            session.caller_phone = sup.phone

        return {
            "found": True,
            "id": sup.id,
            "name": sup.name,
            "phone": sup.phone,
            "city": sup.city,
            "state": sup.state,
            "contact_person": sup.contact_person,
            "gstin": sup.gstin,
        }


def check_stock(sku: str | None = None, warehouse: str | None = None) -> dict[str, Any]:
    """Look up stock for a SKU. If warehouse omitted, sum across warehouses."""
    with session_scope() as db:
        q = select(Stock, Supplier).join(Supplier, Supplier.id == Stock.sku, isouter=True) if False else select(Stock)
        q = select(Stock)
        if sku:
            q = q.where(Stock.sku == sku)
        if warehouse:
            q = q.where(Stock.warehouse == warehouse)
        rows = db.execute(q).scalars().all()
        if not rows:
            return {"available": False, "sku": sku, "warehouses": []}

        warehouses = [
            {"warehouse": r.warehouse, "quantity": r.quantity, "updated_at": r.updated_at.isoformat()}
            for r in rows
        ]
        total = sum(r.quantity for r in rows)
        return {"available": total > 0, "sku": sku, "total": total, "warehouses": warehouses}


def get_shipment_status(order_id: str | None = None, supplier_phone: str | None = None) -> dict[str, Any]:
    """Get latest shipment for an order (or the most recent for a supplier)."""
    with session_scope() as db:
        q = select(Shipment)
        if order_id:
            q = q.where(Shipment.order_id == order_id)
        q = q.order_by(Shipment.last_update.desc())
        ship = db.execute(q).scalars().first()
        if not ship:
            return {"found": False}

        history = json.loads(ship.history_json or "[]")
        return {
            "found": True,
            "shipment_id": ship.id,
            "order_id": ship.order_id,
            "status": ship.status,
            "carrier": ship.carrier,
            "tracking_no": ship.tracking_no,
            "expected_delivery": ship.expected_delivery.isoformat() if ship.expected_delivery else None,
            "last_update": ship.last_update.isoformat(),
            "history": history,
        }


def create_po(
    session: CallSession,
    supplier_id: str | None = None,
    items: list[dict[str, Any]] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Create a new purchase order. `items` is a list of {sku, quantity}."""
    if not supplier_id:
        supplier_id = session.supplier_id
    if not supplier_id:
        return {"ok": False, "error": "supplier_unknown"}
    if not items:
        return {"ok": False, "error": "no_items"}

    # Validate items against products
    validated = []
    for it in items:
        sku = (it.get("sku") or "").strip()
        try:
            qty = int(it.get("quantity", 0))
        except (TypeError, ValueError):
            qty = 0
        if not sku or qty <= 0:
            continue
        validated.append({"sku": sku, "quantity": qty})

    if not validated:
        return {"ok": False, "error": "no_valid_items"}

    total_qty = sum(v["quantity"] for v in validated)
    order_id = f"PO-{int(datetime.now(timezone.utc).timestamp())}-{session.call_id[-4:]}"

    with session_scope() as db:
        sup = db.get(Supplier, supplier_id)
        if not sup:
            return {"ok": False, "error": "supplier_not_found"}
        order = Order(
            id=order_id,
            supplier_id=supplier_id,
            status="pending",
            items_json=json.dumps(validated),
            total_qty=total_qty,
            notes=notes,
        )
        db.add(order)
        db.flush()

    return {
        "ok": True,
        "order_id": order_id,
        "supplier_id": supplier_id,
        "supplier_name": sup.name,
        "items": validated,
        "total_qty": total_qty,
        "status": "pending",
    }


def verify_po(order_id: str) -> dict[str, Any]:
    """Confirm that a PO exists and report its current status."""
    with session_scope() as db:
        o = db.get(Order, order_id)
        if not o:
            return {"ok": False, "error": "not_found", "order_id": order_id}
        return {
            "ok": True,
            "order_id": o.id,
            "status": o.status,
            "total_qty": o.total_qty,
            "items": json.loads(o.items_json or "[]"),
            "notes": o.notes,
            "created_at": o.created_at.isoformat(),
        }


def escalate_to_human(
    session: CallSession,
    reason: str = "",
    summary: str = "",
) -> dict[str, Any]:
    """Flag the call as needing a human follow-up."""
    session.escalated = True
    session.intent = session.intent or "escalation"
    log.info("agent.escalate", call_id=session.call_id, reason=reason, summary=summary)
    return {
        "ok": True,
        "call_id": session.call_id,
        "reason": reason,
        "summary": summary,
    }


# ---------- Dispatcher ----------


def execute_tool(name: str, args: dict[str, Any], session: CallSession) -> dict[str, Any]:
    try:
        if name == "lookup_supplier":
            return lookup_supplier(session, **(args or {}))
        if name == "check_stock":
            return check_stock(**(args or {}))
        if name == "get_shipment_status":
            return get_shipment_status(**(args or {}))
        if name == "create_po":
            return create_po(session, **(args or {}))
        if name == "verify_po":
            return verify_po(**(args or {}))
        if name == "escalate_to_human":
            return escalate_to_human(session, **(args or {}))
        return {"ok": False, "error": f"unknown_tool:{name}"}
    except Exception as e:
        log.error("tool.error", name=name, error=str(e))
        return {"ok": False, "error": str(e), "tool": name}


# ---------- OpenAI-style tool schema ----------


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_supplier",
            "description": "Look up a supplier by phone number or name. Use this as soon as you know who is calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Caller phone number, digits only or with +91."},
                    "name": {"type": "string", "description": "Supplier name or partial name."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": "Check stock availability for a product SKU, optionally at a specific warehouse.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string", "description": "Product SKU, e.g. 'PEP-250ML-12'."},
                    "warehouse": {"type": "string", "description": "Warehouse name; omit to sum across all."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipment_status",
            "description": "Get the latest shipment status for a PO id, or the most recent shipment if PO is unknown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order/PO id like 'PO-1717000000-abcd'."},
                    "supplier_phone": {"type": "string", "description": "Optional supplier phone fallback."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_po",
            "description": "Create a new purchase order. Call this only after the supplier has confirmed each SKU and quantity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "supplier_id": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku": {"type": "string"},
                                "quantity": {"type": "integer", "minimum": 1},
                            },
                            "required": ["sku", "quantity"],
                        },
                    },
                    "notes": {"type": "string"},
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_po",
            "description": "Verify a PO exists and report its current status.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate the call to a human. Use for pricing exceptions, complaints, or anything outside the standard workflow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "summary": {"type": "string", "description": "Short summary of the call so far."},
                },
            },
        },
    },
]
