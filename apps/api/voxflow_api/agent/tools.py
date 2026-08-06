"""Tools the agent can call. Each tool is an async function
backed by the SQLite/Postgres database. Multi-tenant aware via `session.tenant_id`.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..voice.pipeline import CallSession

from sqlalchemy import select

from ..cache import stock_cache, supplier_cache
from ..config import get_settings
from ..db import (
    Appointment,
    CommunicationLog,
    Order,
    Shipment,
    Stock,
    Supplier,
    WorksheetLog,
    async_session_scope,
)
from ..integrations.gsheets import get_sheets_client
from ..logging import get_logger


log = get_logger(__name__)


# ---------- Tool implementations ----------


async def lookup_supplier(session: CallSession, phone: str | None = None, name: str | None = None) -> dict[str, Any]:
    """Find a supplier by phone number or partial name within the active tenant."""
    # `session.verified` MUST be part of the key. The result is redacted before
    # verification and complete after it, so a key that ignores verification
    # state serves one call's data to another: a verified call caches the full
    # record including gstin, and the next unverified caller on the same number
    # is handed it straight out of the cache. Found by
    # tests/test_caller_identification.py, not by inspection.
    cache_key_parts = [session.tenant_id, phone or "", name or "",
                       "v" if session.verified else "u"]
    cached = supplier_cache.get(*cache_key_parts)
    if cached is not None:
        if cached.get("found"):
            session.supplier_id = cached["id"]
            session.caller_name = cached.get("contact_person", "") or cached["name"]
        return cached

    # The model is not reliably given the caller's number, and when it is not it
    # invents a placeholder — we observed it pass the literal string
    # "caller's phone number". Stripping non-digits from that yields "", and
    # `LIKE '%'` matches EVERY supplier, so `.first()` returned an arbitrary
    # company. The agent then greeted the caller by that company's name and,
    # worse, `session.supplier_id` was set to it — which is the record
    # `verify_caller` checks against. Fall back to the real number from the call
    # metadata, and never filter on a fragment too short to identify anyone.
    phone = phone or session.caller_phone
    digits = "".join(c for c in (phone or "") if c.isdigit())[-10:]
    matched_by_phone = False

    async with async_session_scope() as db:
        sup = None
        if len(digits) >= 7:
            q = select(Supplier).where(
                Supplier.tenant_id == session.tenant_id,
                Supplier.phone.like(f"%{digits}"),
            )
            sup = (await db.execute(q)).scalars().first()
            matched_by_phone = sup is not None
        if not sup and name:
            q_name = select(Supplier).where(
                Supplier.tenant_id == session.tenant_id,
                Supplier.name.ilike(f"%{name}%"),
            )
            sup = (await db.execute(q_name)).scalars().first()

        if not sup:
            return {"found": False, "phone": phone, "name": name}

        session.supplier_id = sup.id
        session.caller_name = sup.contact_person or sup.name
        session.identified_by_phone = matched_by_phone
        if not session.caller_phone:
            session.caller_phone = sup.phone

        # Deliberately withhold `city` and `gstin` until verified. Those are
        # precisely the two values `verify_caller` accepts as its second factor.
        # Returning them here put the answers to the security question into the
        # model's context, and a model trying to be helpful will pass back what
        # it just read instead of what the caller actually said — verifying a
        # stranger against a record they never proved any knowledge of.
        # `verify_caller` compares internally; the model never needs to see them.
        # `contact_person` is withheld for the same reason as city and gstin:
        # `verify_caller` accepts the contact name as a corroborating factor, so
        # showing it here is showing the answer. The agent greets generically
        # until the caller has proved who they are — a small loss of warmth for
        # the difference between real verification and theatre.
        result = {
            "found": True,
            "id": sup.id,
            "name": sup.name,
            "matched_by": "phone" if matched_by_phone else "name",
        }
        if session.verified:
            result.update({"phone": sup.phone, "city": sup.city,
                           "state": sup.state, "gstin": sup.gstin})
        supplier_cache.set(*cache_key_parts, value=result)
        return result


MAX_VERIFY_ATTEMPTS = 3


def _norm(text: str) -> str:
    """Lowercase, strip punctuation/whitespace — for fuzzy spoken-answer matching.

    Speech-to-text output is messy: "Pvt. Ltd." becomes "pvt ltd", GSTINs come
    through with spaces between characters. Normalising both sides before
    comparison avoids rejecting a legitimate caller over a transcription artifact.
    """
    return "".join(c for c in (text or "").lower() if c.isalnum())


async def verify_caller(
    session: CallSession,
    company: str | None = None,
    city_or_gstin: str | None = None,
    contact_name: str | None = None,
) -> dict[str, Any]:
    """Two-factor caller verification.

    Factor 1 (implicit): the inbound phone number already matched a contact
    record via `lookup_supplier`.
    Factor 2 (explicit): the caller must state the company they work for AND
    one corroborating detail — their city, their GSTIN, or their own name as
    recorded against the account.

    Only flips `session.verified` when the company matches AND at least one
    corroborating detail matches. Attempts are capped and counted, so a caller
    fishing for another company's order data gets locked out and logged.
    """
    if not session.supplier_id:
        return {"verified": False, "reason": "caller_not_identified"}

    if session.verify_attempts >= MAX_VERIFY_ATTEMPTS:
        session.escalated = True
        log.warning(
            "verify.locked_out",
            call_id=session.call_id,
            phone=session.caller_phone,
            attempts=session.verify_attempts,
        )
        return {
            "verified": False,
            "reason": "too_many_attempts",
            "locked": True,
            "message": "Verification attempt limit reached. Transfer to a human.",
        }

    session.verify_attempts += 1

    async with async_session_scope() as db:
        sup = await db.get(Supplier, session.supplier_id)
        if not sup or sup.tenant_id != session.tenant_id:
            return {"verified": False, "reason": "contact_not_found"}

        company_ok = False
        if company:
            c = _norm(company)
            rec = _norm(sup.name)
            # Accept a substring match in either direction — callers say
            # "Varun Beverages" for a record reading "Varun Beverages Pvt Ltd".
            company_ok = bool(c) and (c in rec or rec in c)

        detail_ok = False
        matched_on = None
        if city_or_gstin:
            v = _norm(city_or_gstin)
            if v and v in _norm(sup.city):
                detail_ok, matched_on = True, "city"
            elif v and sup.gstin and v in _norm(sup.gstin):
                detail_ok, matched_on = True, "gstin"
        if not detail_ok and contact_name:
            n = _norm(contact_name)
            if n and sup.contact_person and (n in _norm(sup.contact_person) or _norm(sup.contact_person) in n):
                detail_ok, matched_on = True, "contact_name"

        if company_ok and detail_ok:
            session.verified = True
            session.company_name = sup.name
            if contact_name:
                session.caller_name = contact_name
            log.info(
                "verify.success",
                call_id=session.call_id,
                supplier_id=sup.id,
                matched_on=matched_on,
                # False means the inbound number did NOT match this record, so
                # verification rested entirely on what the caller stated. Still
                # legitimate — they proved knowledge of a detail we never told
                # them — but worth being able to audit after the fact.
                identified_by_phone=session.identified_by_phone,
            )
            return {
                "verified": True,
                "company": sup.name,
                "contact_person": sup.contact_person,
                "matched_on": matched_on,
                "attempts_used": session.verify_attempts,
            }

        log.warning(
            "verify.failed",
            call_id=session.call_id,
            company_ok=company_ok,
            detail_ok=detail_ok,
            attempt=session.verify_attempts,
        )
        missing = []
        if not company_ok:
            missing.append("company")
        if not detail_ok:
            missing.append("city_or_gstin_or_name")
        return {
            "verified": False,
            "reason": "mismatch",
            "missing": missing,
            "attempts_used": session.verify_attempts,
            "attempts_remaining": MAX_VERIFY_ATTEMPTS - session.verify_attempts,
        }


async def check_stock(session: CallSession, sku: str | None = None, warehouse: str | None = None) -> dict[str, Any]:
    """Look up stock for a SKU within the active tenant."""
    cache_key_parts = [session.tenant_id, sku or "*", warehouse or "*"]
    cached = stock_cache.get(*cache_key_parts)
    if cached is not None:
        return cached

    async with async_session_scope() as db:
        q = select(Stock).where(Stock.tenant_id == session.tenant_id)
        if sku:
            q = q.where(Stock.sku == sku)
        if warehouse:
            q = q.where(Stock.warehouse == warehouse)
        rows = (await db.execute(q)).scalars().all()
        if not rows:
            return {"available": False, "sku": sku, "warehouses": []}

        warehouses = [
            {"warehouse": r.warehouse, "quantity": r.quantity, "updated_at": r.updated_at.isoformat()}
            for r in rows
        ]
        total = sum(r.quantity for r in rows)
        result = {"available": total > 0, "sku": sku, "total": total, "warehouses": warehouses}
        stock_cache.set(*cache_key_parts, value=result)
        return result


async def get_shipment_status(session: CallSession, order_id: str | None = None, supplier_phone: str | None = None) -> dict[str, Any]:
    """Get latest shipment for an order within the active tenant."""
    async with async_session_scope() as db:
        q = select(Shipment).where(Shipment.tenant_id == session.tenant_id)
        if order_id:
            q = q.where(Shipment.order_id == order_id)
        q = q.order_by(Shipment.last_update.desc())
        ship = (await db.execute(q)).scalars().first()
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


async def create_po(
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

    stock_cache.clear()

    async with async_session_scope() as db:
        sup = await db.get(Supplier, supplier_id)
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
        await db.flush()

    return {
        "ok": True,
        "order_id": order_id,
        "supplier_id": supplier_id,
        "supplier_name": sup.name,
        "items": validated,
        "total_qty": total_qty,
        "status": "pending",
    }


async def verify_po(session: CallSession, order_id: str) -> dict[str, Any]:
    """Confirm that a PO exists in the tenant's records."""
    async with async_session_scope() as db:
        o = await db.get(Order, order_id)
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


async def _resolve_order(db: Any, session: CallSession, order_id: str | None, customer_po_ref: str | None) -> Order | None:
    """Find an order by our ID or by the customer's own PO reference.

    Always scoped to the active tenant AND to the caller's own contact record —
    a verified caller from company A must never be able to read company B's
    order by guessing an ID.
    """
    q = select(Order).where(Order.tenant_id == session.tenant_id)
    if session.supplier_id:
        q = q.where(Order.supplier_id == session.supplier_id)

    if order_id:
        oid = order_id.strip()
        row = (await db.execute(q.where(Order.id == oid))).scalars().first()
        if row:
            return row
    if customer_po_ref:
        ref = customer_po_ref.strip()
        row = (await db.execute(q.where(Order.customer_po_ref.ilike(f"%{ref}%")))).scalars().first()
        if row:
            return row
    return None


async def check_po_status(
    session: CallSession,
    order_id: str | None = None,
    customer_po_ref: str | None = None,
) -> dict[str, Any]:
    """Report whether a PO has been signed, its quantity, and when it was signed.

    This is the "have we signed your PO yet?" question — the most common
    inbound B2B query.
    """
    if not session.verified:
        return {"ok": False, "error": "not_verified", "message": "Verify the caller before sharing order data."}
    if not order_id and not customer_po_ref:
        return {"ok": False, "error": "no_reference", "message": "Ask the caller for their PO number."}

    async with async_session_scope() as db:
        o = await _resolve_order(db, session, order_id, customer_po_ref)
        if not o:
            return {"ok": False, "error": "not_found", "order_id": order_id, "customer_po_ref": customer_po_ref}

        session.related_order = o.id
        return {
            "ok": True,
            "order_id": o.id,
            "customer_po_ref": o.customer_po_ref,
            "po_signed": bool(o.po_signed),
            "po_signed_at": o.po_signed_at.isoformat() if o.po_signed_at else None,
            "po_signed_by": o.po_signed_by,
            "status": o.status,
            "total_qty": o.total_qty,
            "items": json.loads(o.items_json or "[]"),
            "placed_on": o.created_at.isoformat(),
        }


async def get_order_details(
    session: CallSession,
    order_id: str | None = None,
    customer_po_ref: str | None = None,
) -> dict[str, Any]:
    """Full order picture: quantity, dispatch date, and where the shipment has reached.

    Answers "when did you send it and where has it got to?" in one tool call,
    so the agent doesn't need two round-trips mid-conversation.
    """
    if not session.verified:
        return {"ok": False, "error": "not_verified", "message": "Verify the caller before sharing order data."}
    if not order_id and not customer_po_ref:
        return {"ok": False, "error": "no_reference", "message": "Ask the caller for their PO number."}

    async with async_session_scope() as db:
        o = await _resolve_order(db, session, order_id, customer_po_ref)
        if not o:
            return {"ok": False, "error": "not_found", "order_id": order_id, "customer_po_ref": customer_po_ref}

        session.related_order = o.id

        ship = (
            await db.execute(
                select(Shipment)
                .where(Shipment.tenant_id == session.tenant_id, Shipment.order_id == o.id)
                .order_by(Shipment.last_update.desc())
            )
        ).scalars().first()

        result: dict[str, Any] = {
            "ok": True,
            "order_id": o.id,
            "customer_po_ref": o.customer_po_ref,
            "status": o.status,
            "total_qty": o.total_qty,
            "items": json.loads(o.items_json or "[]"),
            "placed_on": o.created_at.isoformat(),
            "po_signed": bool(o.po_signed),
            "dispatched_at": o.dispatched_at.isoformat() if o.dispatched_at else None,
            "shipment": None,
        }

        if ship:
            history = json.loads(ship.history_json or "[]")
            # The most recent history entry is "where it has reached right now".
            current_location = ""
            if history:
                last = history[-1]
                current_location = last.get("location") or last.get("status") or ""
            result["shipment"] = {
                "shipment_id": ship.id,
                "status": ship.status,
                "carrier": ship.carrier,
                "tracking_no": ship.tracking_no,
                "current_location": current_location,
                "expected_delivery": ship.expected_delivery.isoformat() if ship.expected_delivery else None,
                "last_update": ship.last_update.isoformat(),
                "history": history,
            }
        return result


async def log_call_outcome(
    session: CallSession,
    reason: str,
    solution: str,
    resolution_status: str,
    satisfaction: str = "neutral",
    follow_up_required: bool = False,
    related_order: str = "",
) -> dict[str, Any]:
    """Record why the caller rang, what was done, and whether they were happy.

    Writes to the session (persisted to Postgres on call end) and mirrors the
    row into Google Sheets for the ops team. A Sheets failure is logged but
    never fails the call.
    """
    valid_resolution = {"resolved", "partial", "unresolved"}
    valid_satisfaction = {"happy", "neutral", "unhappy"}

    resolution_status = (resolution_status or "").strip().lower()
    satisfaction = (satisfaction or "neutral").strip().lower()
    if resolution_status not in valid_resolution:
        resolution_status = "partial"
    if satisfaction not in valid_satisfaction:
        satisfaction = "neutral"

    session.reason = reason
    session.solution = solution
    session.resolution_status = resolution_status
    session.satisfaction = satisfaction
    session.follow_up_required = bool(follow_up_required)
    if related_order:
        session.related_order = related_order
    if not session.intent:
        session.intent = reason[:64]
    session.outcome = resolution_status

    duration = int(time.time() - session.started_at)
    ist = timezone(timedelta(hours=5, minutes=30))
    row = {
        "timestamp": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
        "call_id": session.call_id,
        "caller_phone": session.caller_phone,
        "caller_name": session.caller_name,
        "company": session.company_name,
        "verified": session.verified,
        "language": session.language,
        "reason": reason,
        "solution": solution,
        "resolution_status": resolution_status,
        "satisfaction": satisfaction,
        "follow_up_required": session.follow_up_required,
        "escalated": session.escalated,
        "duration_sec": duration,
        "related_order": session.related_order,
    }

    # Fire the Sheets write in the BACKGROUND. This tool runs while the caller
    # is still on the line, and a slow Google response would otherwise be heard
    # as dead air — the worst failure mode this product has. The task is handed
    # to the session so end_session() can drain it after the caller hangs up,
    # which keeps `sheet_synced` accurate without costing the caller anything.
    #
    # If the process dies before the task completes, the row is still safe in
    # Postgres with sheet_synced=0, so it is recoverable and visible.
    sheet_pending = False
    if get_sheets_client().is_configured():
        try:
            session.sheet_task = asyncio.create_task(
                get_sheets_client().append_call_outcome(row)
            )
            sheet_pending = True
        except RuntimeError:
            # No running loop (direct/synchronous invocation, e.g. a test).
            result = await get_sheets_client().append_call_outcome(row)
            session.sheet_synced = bool(result.get("ok"))
    else:
        session.sheet_synced = False

    # Always keep a local audit row, even when Sheets is off or failing.
    async with async_session_scope() as db:
        db.add(
            WorksheetLog(
                tenant_id=session.tenant_id,
                worksheet_name=get_settings().google_sheet_tab,
                action_type="append",
                row_data_json=json.dumps(row, default=str),
            )
        )

    log.info(
        "call.outcome_logged",
        call_id=session.call_id,
        resolution=resolution_status,
        satisfaction=satisfaction,
        sheet="pending" if sheet_pending else ("ok" if session.sheet_synced else "off"),
    )
    return {
        "ok": True,
        "logged": True,
        "resolution_status": resolution_status,
        "satisfaction": satisfaction,
        # "pending" tells the model the write is in flight so it doesn't claim
        # to the caller that the record is definitely filed.
        "sheet_synced": "pending" if sheet_pending else session.sheet_synced,
    }


async def schedule_appointment(session: CallSession, datetime_str: str, purpose: str = "") -> dict[str, Any]:
    """Schedule a supplier appointment."""
    app_id = f"app-{uuid.uuid4().hex[:6]}"
    try:
        dt = datetime.fromisoformat(datetime_str)
    except Exception:
        return {"ok": False, "error": "invalid_datetime", "appointment_id": None}

    async with async_session_scope() as db:
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


async def send_email(session: CallSession, to_address: str, subject: str, body: str) -> dict[str, Any]:
    """Send an email notification."""
    comm_id = f"comm-email-{uuid.uuid4().hex[:6]}"
    async with async_session_scope() as db:
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


async def send_whatsapp_message(session: CallSession, to_phone: str, message: str) -> dict[str, Any]:
    """Send a WhatsApp message notification."""
    comm_id = f"comm-wa-{uuid.uuid4().hex[:6]}"
    async with async_session_scope() as db:
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


async def update_worksheet(session: CallSession, worksheet_name: str, action: str, row_data: dict[str, Any]) -> dict[str, Any]:
    """Append an ad-hoc row to a Google Sheets tab, plus a local audit entry.

    For the standard call-outcome row prefer `log_call_outcome` — it enforces
    the canonical column order. This tool is the escape hatch for anything else
    the ops team wants captured on a sheet.
    """
    async with async_session_scope() as db:
        db.add(
            WorksheetLog(
                tenant_id=session.tenant_id,
                worksheet_name=worksheet_name,
                action_type=action,
                row_data_json=json.dumps(row_data, default=str),
            )
        )

    sheet_result: dict[str, Any] = {"ok": False, "reason": "skipped"}
    if action == "append" and row_data:
        # Stable column order: sorted keys, so repeated calls line up.
        keys = sorted(row_data.keys())
        sheet_result = await get_sheets_client().append_row(
            [row_data[k] for k in keys],
            tab=worksheet_name,
            headers=keys,
        )

    return {
        "ok": True,
        "worksheet": worksheet_name,
        "action": action,
        "sheet_synced": bool(sheet_result.get("ok")),
    }


async def type_notes(session: CallSession, text: str) -> dict[str, Any]:
    """Record free-form notes during a call."""
    log.info("notes.typed", text=text)
    return {"ok": True, "note": text}


async def escalate_to_human(session: CallSession, reason: str = "", summary: str = "") -> dict[str, Any]:
    """Flag the call as needing a human follow-up."""
    session.escalated = True
    session.intent = session.intent or "escalation"
    log.info("agent.escalate", call_id=session.call_id, reason=reason, summary=summary)
    return {"ok": True, "call_id": session.call_id, "reason": reason, "summary": summary}


# ---------- Dispatcher ----------


async def execute_tool(name: str, args: dict[str, Any], session: CallSession) -> dict[str, Any]:
    try:
        if name == "lookup_supplier":
            return await lookup_supplier(session, **(args or {}))
        if name == "verify_caller":
            return await verify_caller(session, **(args or {}))
        if name == "check_stock":
            return await check_stock(session, **(args or {}))
        if name == "get_shipment_status":
            return await get_shipment_status(session, **(args or {}))
        if name == "create_po":
            return await create_po(session, **(args or {}))
        if name == "verify_po":
            return await verify_po(session, **(args or {}))
        if name == "check_po_status":
            return await check_po_status(session, **(args or {}))
        if name == "get_order_details":
            return await get_order_details(session, **(args or {}))
        if name == "log_call_outcome":
            return await log_call_outcome(session, **(args or {}))
        if name == "schedule_appointment":
            return await schedule_appointment(session, **(args or {}))
        if name == "send_email":
            return await send_email(session, **(args or {}))
        if name == "send_whatsapp_message":
            return await send_whatsapp_message(session, **(args or {}))
        if name == "update_worksheet":
            return await update_worksheet(session, **(args or {}))
        if name == "type_notes":
            return await type_notes(session, **(args or {}))
        if name == "escalate_to_human":
            return await escalate_to_human(session, **(args or {}))
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
            "description": (
                "Verify the caller's identity before sharing ANY order or PO information. "
                "Requires the company they work for PLUS one corroborating detail "
                "(their city, their GSTIN, or their own name on the account). "
                "Call this once you have collected both from the caller."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "The company the caller says they work for.",
                    },
                    "city_or_gstin": {
                        "type": "string",
                        "description": "The caller's city or GSTIN, as spoken.",
                    },
                    "contact_name": {
                        "type": "string",
                        "description": "The caller's own name, if given.",
                    },
                },
                "required": ["company"],
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
            "name": "check_po_status",
            "description": (
                "Check whether a purchase order has been SIGNED, its quantity, and when it was signed. "
                "Use this for questions like 'have you signed my PO yet?' or 'is my order confirmed?'. "
                "Requires the caller to be verified first. Accepts either our order ID or the "
                "customer's own PO reference number."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Our internal order ID, e.g. PO-1738000000-a1b2."},
                    "customer_po_ref": {
                        "type": "string",
                        "description": "The customer's own PO number, e.g. VB/PO/2026/0912.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_details",
            "description": (
                "Get the full picture of an order: quantity, items, whether the PO is signed, "
                "when it was dispatched, and where the shipment has currently reached. "
                "Use this for 'when did you send it?' and 'where has my order reached?'. "
                "Requires the caller to be verified first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "customer_po_ref": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_call_outcome",
            "description": (
                "MANDATORY before the call ends. Records why the caller rang, what solution you gave, "
                "whether it resolved their query, and whether they sounded satisfied. "
                "Writes to the company's Google Sheet call log. Call this exactly once, "
                "after you have answered the caller's question and confirmed with them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why they called, one short sentence in English.",
                    },
                    "solution": {
                        "type": "string",
                        "description": "What you told them or did for them, one short sentence in English.",
                    },
                    "resolution_status": {
                        "type": "string",
                        "enum": ["resolved", "partial", "unresolved"],
                        "description": "resolved = they got what they needed; partial = answered but follow-up needed; unresolved = could not help.",
                    },
                    "satisfaction": {
                        "type": "string",
                        "enum": ["happy", "neutral", "unhappy"],
                        "description": "Judge from their tone and words: did the answer satisfy them?",
                    },
                    "follow_up_required": {
                        "type": "boolean",
                        "description": "True if a human needs to call them back.",
                    },
                    "related_order": {
                        "type": "string",
                        "description": "Order ID or customer PO reference this call was about, if any.",
                    },
                },
                "required": ["reason", "solution", "resolution_status", "satisfaction"],
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
