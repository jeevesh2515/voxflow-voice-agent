"""Tools the agent can call. Each tool is a Python function
backed by the SQLite/Postgres database. Multi-tenant aware via `session.tenant_id`.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from ..db import (
    Appointment,
    CommunicationLog,
    Order,
    Shipment,
    Stock,
    Supplier,
    WorksheetLog,
    session_scope,
)
from ..logging import get_logger
from ..voice.pipeline import CallSession


log = get_logger(__name__)


# ---------- Tool implementations ----------


def lookup_supplier(session: CallSession, phone: str | None = None, name: str | None = None) -> dict[str, Any]:
    """Find a supplier by phone number or partial name within the active tenant."""
    with session_scope() as db:
        q = select(Supplier).where(Supplier.tenant_id == session.tenant_id)
        if phone:
            digits = "".join(c for c in phone if c.isdigit())[-10:]
            q = q.where(Supplier.phone.like(f"%{digits}"))
        sup = db.execute(q).scalars().first()
        if not sup and name:
            q_name = select(Supplier).where(
                Supplier.tenant_id == session.tenant_id,
                Supplier.name.ilike(f"%{name}%"),
            )
            sup = db.execute(q_name).scalars().first()

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


def verify_caller(session: CallSession, city_or_gstin: str) -> dict[str, Any]:
    """Verify caller identity against supplier records."""
    if not session.supplier_id:
        return {"verified": False, "reason": "supplier_unknown"}

    with session_scope() as db:
        sup = db.get(Supplier, session.supplier_id)
        if not sup:
            return {"verified": False, "reason": "supplier_not_found"}

        val = city_or_gstin.strip().lower()
        if val in sup.city.lower() or (sup.gstin and val in sup.gstin.lower()):
            return {"verified": True, "supplier_name": sup.name}

    return {"verified": False, "reason": "mismatch"}


def check_stock(session: CallSession, sku: str | None = None, warehouse: str | None = None) -> dict[str, Any]:
    """Look up stock for a SKU within the active tenant."""
    with session_scope() as db:
        q = select(Stock).where(Stock.tenant_id == session.tenant_id)
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


def get_shipment_status(session: CallSession, order_id: str | None = None, supplier_phone: str | None = None) -> dict[str, Any]:
    """Get latest shipment for an order within the active tenant."""
    with session_scope() as db:
        q = select(Shipment).where(Shipment.tenant_id == session.tenant_id)
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
    """Create a new purchase order within the active tenant."""
    if not supplier_id:
        supplier_id = session.supplier_id
    if not supplier_id:
        return {"ok": False, "error": "supplier_unknown"}
    if not items:
        return {"ok": False, "error": "no_items"}

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
            tenant_id=session.tenant_id,
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


def verify_po(session: CallSession, order_id: str) -> dict[str, Any]:
    """Confirm that a PO exists in the tenant's records."""
    with session_scope() as db:
        o = db.get(Order, order_id)
        if not o or o.tenant_id != session.tenant_id:
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


def schedule_appointment(session: CallSession, datetime_str: str, purpose: str = "") -> dict[str, Any]:
    """Schedule a supplier appointment."""
    app_id = f"app-{uuid.uuid4().hex[:6]}"
    try:
        dt = datetime.fromisoformat(datetime_str)
    except Exception:
        dt = datetime.now(timezone.utc)

    with session_scope() as db:
        app = Appointment(
            id=app_id,
            tenant_id=session.tenant_id,
            supplier_id=session.supplier_id,
            datetime=dt,
            purpose=purpose,
            status="confirmed",
        )
        db.add(app)

    return {"ok": True, "appointment_id": app_id, "datetime": dt.isoformat(), "purpose": purpose}


def send_email(session: CallSession, to_address: str, subject: str, body: str) -> dict[str, Any]:
    """Send an email notification."""
    comm_id = f"comm-email-{uuid.uuid4().hex[:6]}"
    with session_scope() as db:
        comm = CommunicationLog(
            id=comm_id,
            tenant_id=session.tenant_id,
            channel="email",
            recipient=to_address,
            subject=subject,
            body=body,
            status="sent",
        )
        db.add(comm)

    log.info("email.sent", to=to_address, subject=subject)
    return {"ok": True, "comm_id": comm_id, "channel": "email", "recipient": to_address}


def send_whatsapp_message(session: CallSession, to_phone: str, message: str) -> dict[str, Any]:
    """Send a WhatsApp message notification."""
    comm_id = f"comm-wa-{uuid.uuid4().hex[:6]}"
    with session_scope() as db:
        comm = CommunicationLog(
            id=comm_id,
            tenant_id=session.tenant_id,
            channel="whatsapp",
            recipient=to_phone,
            subject=None,
            body=message,
            status="sent",
        )
        db.add(comm)

    log.info("whatsapp.sent", to=to_phone, message=message)
    return {"ok": True, "comm_id": comm_id, "channel": "whatsapp", "recipient": to_phone}


def update_worksheet(session: CallSession, worksheet_name: str, action: str, row_data: dict[str, Any]) -> dict[str, Any]:
    """Record an audit entry in the worksheet log."""
    with session_scope() as db:
        log_entry = WorksheetLog(
            tenant_id=session.tenant_id,
            worksheet_name=worksheet_name,
            action_type=action,
            row_data_json=json.dumps(row_data),
        )
        db.add(log_entry)

    return {"ok": True, "worksheet": worksheet_name, "action": action}


def type_notes(session: CallSession, text: str) -> dict[str, Any]:
    """Record free-form notes during a call."""
    log.info("notes.typed", text=text)
    return {"ok": True, "note": text}


def escalate_to_human(session: CallSession, reason: str = "", summary: str = "") -> dict[str, Any]:
    """Flag the call as needing a human follow-up."""
    session.escalated = True
    session.intent = session.intent or "escalation"
    log.info("agent.escalate", call_id=session.call_id, reason=reason, summary=summary)
    return {"ok": True, "call_id": session.call_id, "reason": reason, "summary": summary}


# ---------- Dispatcher ----------


def execute_tool(name: str, args: dict[str, Any], session: CallSession) -> dict[str, Any]:
    try:
        if name == "lookup_supplier":
            return lookup_supplier(session, **(args or {}))
        if name == "verify_caller":
            return verify_caller(session, **(args or {}))
        if name == "check_stock":
            return check_stock(session, **(args or {}))
        if name == "get_shipment_status":
            return get_shipment_status(session, **(args or {}))
        if name == "create_po":
            return create_po(session, **(args or {}))
        if name == "verify_po":
            return verify_po(session, **(args or {}))
        if name == "schedule_appointment":
            return schedule_appointment(session, **(args or {}))
        if name == "send_email":
            return send_email(session, **(args or {}))
        if name == "send_whatsapp_message":
            return send_whatsapp_message(session, **(args or {}))
        if name == "update_worksheet":
            return update_worksheet(session, **(args or {}))
        if name == "type_notes":
            return type_notes(session, **(args or {}))
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
            "description": "Look up a supplier by phone number or name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_caller",
            "description": "Verify caller identity against company city or GSTIN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_or_gstin": {"type": "string"},
                },
                "required": ["city_or_gstin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": "Check stock availability for a SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string"},
                    "warehouse": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipment_status",
            "description": "Get latest shipment status for a PO.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_po",
            "description": "Create a new purchase order.",
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
            "description": "Verify PO status.",
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
            "name": "schedule_appointment",
            "description": "Schedule a supplier appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "datetime_str": {"type": "string"},
                    "purpose": {"type": "string"},
                },
                "required": ["datetime_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email notification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_address": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to_address", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp_message",
            "description": "Send a WhatsApp message to the supplier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_phone": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["to_phone", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_worksheet",
            "description": "Log an entry in a spreadsheet worksheet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "worksheet_name": {"type": "string"},
                    "action": {"type": "string"},
                    "row_data": {"type": "object"},
                },
                "required": ["worksheet_name", "action", "row_data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_notes",
            "description": "Record free-form notes during call.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate to human.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "summary": {"type": "string"},
                },
            },
        },
    },
]
