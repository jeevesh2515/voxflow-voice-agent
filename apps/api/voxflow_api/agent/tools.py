"""Tools the agent can call. Each tool is an async function
backed by the SQLite/Postgres database. Multi-tenant aware via `session.tenant_id`.
"""

from __future__ import annotations

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
    Tenant,
    WorksheetLog,
    async_session_scope,
)
from ..jobs.side_effects import (
    CRM_WEBHOOK_SYNC,
    NOTIFICATION_DISPATCH,
    SHEETS_CALL_OUTCOME,
    SHEETS_WORKSHEET_APPEND,
    enqueue_side_effect_async,
)
from ..integrations.gsheets import get_sheets_client
from ..logging import get_logger
from ..services.pin_security import hash_pin, redact_pin_text, verify_legacy_pin, verify_pin_hash


log = get_logger(__name__)


_KNOWLEDGE_BINDING_KEY = "_knowledge_verified_supplier_id"
_PIN_BINDING_KEY = "_pin_verified_supplier_id"


def _authorization_policy(session: CallSession) -> dict[str, str]:
    """Return the session-persisted authorization binding store."""
    if not isinstance(session.route_policy, dict):
        session.route_policy = {}
    return session.route_policy


def _bound_supplier_id(session: CallSession, key: str) -> str | None:
    supplier_id = _authorization_policy(session).get(key)
    return supplier_id if isinstance(supplier_id, str) and supplier_id else None


def _bind_authorization(session: CallSession, key: str, supplier_id: str) -> None:
    _authorization_policy(session)[key] = supplier_id


def _clear_authorization(session: CallSession) -> None:
    """Invalidate both factors and their contact bindings."""
    session.verified = False
    session.pin_verified = False
    policy = _authorization_policy(session)
    policy.pop(_KNOWLEDGE_BINDING_KEY, None)
    policy.pop(_PIN_BINDING_KEY, None)


def _identify_supplier(
    session: CallSession,
    supplier_id: str | None,
    *,
    caller_name: str = "",
    identified_by_phone: bool = False,
) -> None:
    """Set the identified contact, invalidating authorization on any change."""
    if supplier_id is None or supplier_id != session.supplier_id:
        _clear_authorization(session)
        session.company_name = ""
    session.supplier_id = supplier_id
    session.identified_by_phone = identified_by_phone if supplier_id else False
    if supplier_id:
        session.caller_name = caller_name
    else:
        session.caller_name = ""


def _knowledge_authorized_supplier_id(session: CallSession) -> str | None:
    supplier_id = session.supplier_id
    if (
        supplier_id
        and session.verified
        and _bound_supplier_id(session, _KNOWLEDGE_BINDING_KEY) == supplier_id
    ):
        return supplier_id
    return None


def _pin_authorized_supplier_id(session: CallSession) -> str | None:
    supplier_id = session.supplier_id
    if (
        supplier_id
        and session.pin_verified
        and _bound_supplier_id(session, _PIN_BINDING_KEY) == supplier_id
    ):
        return supplier_id
    return None


# ---------- Tool implementations ----------


async def lookup_supplier(session: CallSession, phone: str | None = None, name: str | None = None) -> dict[str, Any]:
    """Find a supplier by phone number or partial name within the active tenant."""
    # The exact knowledge-verification binding MUST be part of the key. The
    # result is redacted before verification and complete afterward, so a key
    # that ignores the binding can serve a verified caller's GSTIN to another
    # call or to the wrong identified contact.
    verified_supplier_id = _knowledge_authorized_supplier_id(session)
    cache_key_parts = [
        session.tenant_id,
        phone or "",
        name or "",
        verified_supplier_id or "u",
    ]
    cached = supplier_cache.get(*cache_key_parts)
    if cached is not None:
        if not cached.get("found"):
            _identify_supplier(session, None)
            return cached

        result = dict(cached)
        _identify_supplier(
            session,
            result["id"],
            caller_name=result.get("contact_person", "") or result["name"],
            identified_by_phone=result.get("matched_by") == "phone",
        )
        if _knowledge_authorized_supplier_id(session) != result["id"]:
            for field in ("phone", "city", "state", "gstin", "contact_person"):
                result.pop(field, None)
        return result

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
            _identify_supplier(session, None)
            return {"found": False, "phone": phone, "name": name}

        _identify_supplier(
            session,
            sup.id,
            caller_name=sup.contact_person or sup.name,
            identified_by_phone=matched_by_phone,
        )
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
        if _knowledge_authorized_supplier_id(session) == sup.id:
            result.update(
                {
                    "phone": sup.phone,
                    "city": sup.city,
                    "state": sup.state,
                    "gstin": sup.gstin,
                }
            )
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
        sup = (
            await db.execute(
                select(Supplier).where(
                    Supplier.tenant_id == session.tenant_id,
                    Supplier.id == session.supplier_id,
                )
            )
        ).scalars().first()
        if not sup:
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
            _bind_authorization(session, _KNOWLEDGE_BINDING_KEY, sup.id)
            if _bound_supplier_id(session, _PIN_BINDING_KEY) != sup.id:
                session.pin_verified = False
                _authorization_policy(session).pop(_PIN_BINDING_KEY, None)
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


MAX_PIN_ATTEMPTS = 3
# A `CallSession`-scoped counter alone cannot stop brute forcing across many
# fresh calls/sessions — every new call (and every unauthenticated /agent/run
# request) starts with zero attempts. These two constants back a persistent,
# per-contact lockout stored on the `Supplier` row itself, so guessing a
# 4–8 digit PIN costs an attacker real lockout time, not just a new call.
PERSISTENT_MAX_FAILED_PIN_ATTEMPTS = 10
PERSISTENT_PIN_LOCKOUT_MINUTES = 15


async def verify_pin(session: CallSession, pin: str | None = None) -> dict[str, Any]:
    """Verify a caller's 4–8 digit security PIN for protected reads and writes."""
    if not session.supplier_id:
        return {"verified": False, "reason": "caller_not_identified", "message": "Caller record not identified yet."}

    if session.pin_attempts >= MAX_PIN_ATTEMPTS:
        session.escalated = True
        log.warning("verify_pin.locked_out", call_id=session.call_id, attempts=session.pin_attempts)
        return {
            "verified": False,
            "reason": "too_many_attempts",
            "locked": True,
            "message": "Maximum PIN verification attempts exceeded. Transferring to human agent.",
        }

    session.pin_attempts += 1
    submitted_pin = (pin or "").strip()

    async with async_session_scope() as db:
        # Lock the row for the remainder of this transaction on Postgres so
        # concurrent guesses against the same contact (many parallel calls,
        # or scripted /agent/run requests) serialize through the persistent
        # attempt counter instead of racing on a stale read. SQLite has no
        # equivalent row-level lock and does not need one: its writer
        # transactions are already serialized at the database-file level.
        pin_lookup_query = select(Supplier).where(
            Supplier.tenant_id == session.tenant_id,
            Supplier.id == session.supplier_id,
        )
        if db.get_bind().dialect.name != "sqlite":
            pin_lookup_query = pin_lookup_query.with_for_update()
        sup = (await db.execute(pin_lookup_query)).scalars().first()
        if not sup:
            return {"verified": False, "reason": "contact_not_found"}

        now = datetime.now(timezone.utc)
        locked_until = sup.pin_locked_until
        if locked_until is not None and locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until is not None and locked_until > now:
            session.escalated = True
            log.warning(
                "verify_pin.persistent_lock_active",
                call_id=session.call_id,
                supplier_id=sup.id,
                locked_until=locked_until.isoformat(),
            )
            return {
                "verified": False,
                "reason": "too_many_attempts",
                "locked": True,
                "message": "This contact's PIN is temporarily locked after repeated failed attempts. Transferring to human agent.",
            }

        hash_verified = verify_pin_hash(submitted_pin, sup.auth_pin_hash)
        legacy_verified = not sup.auth_pin_hash and verify_legacy_pin(submitted_pin, sup.auth_pin)
        if hash_verified or legacy_verified:
            if legacy_verified:
                # Successful use is the safest opportunity to migrate a legacy
                # plaintext credential without breaking existing callers.
                sup.auth_pin_hash = hash_pin(submitted_pin)
                sup.auth_pin = None
                sup.pin_updated_at = now
            sup.pin_failed_attempts = 0
            sup.pin_locked_until = None
            session.pin_verified = True
            _bind_authorization(session, _PIN_BINDING_KEY, sup.id)
            log.info("verify_pin.success", call_id=session.call_id, supplier_id=sup.id)
            return {
                "verified": True,
                "message": "PIN verified successfully. Tier 2 authorization granted.",
                "attempts_used": session.pin_attempts,
            }

        sup.pin_failed_attempts = (sup.pin_failed_attempts or 0) + 1
        if sup.pin_failed_attempts >= PERSISTENT_MAX_FAILED_PIN_ATTEMPTS:
            sup.pin_locked_until = now + timedelta(minutes=PERSISTENT_PIN_LOCKOUT_MINUTES)
            log.warning(
                "verify_pin.persistent_lock_engaged",
                call_id=session.call_id,
                supplier_id=sup.id,
                locked_until=sup.pin_locked_until.isoformat(),
            )
        log.warning("verify_pin.failed", call_id=session.call_id, attempt=session.pin_attempts)
        return {
            "verified": False,
            "reason": "invalid_pin",
            "attempts_used": session.pin_attempts,
            "attempts_remaining": MAX_PIN_ATTEMPTS - session.pin_attempts,
            "message": "Incorrect PIN provided. Please ask the caller to double check their 4–8 digit PIN.",
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


def _sensitive_read_denial(session: CallSession) -> dict[str, Any] | None:
    """Require authorization factors bound to the currently identified contact."""
    supplier_id = _knowledge_authorized_supplier_id(session)
    if supplier_id is None:
        return {
            "ok": False,
            "error": "not_verified",
            "message": "Verify the caller before sharing order data.",
        }
    if (
        session.verification_mode == "enhanced"
        and _pin_authorized_supplier_id(session) != supplier_id
    ):
        return {
            "ok": False,
            "error": "pin_required",
            "message": "Enhanced verification requires a valid PIN before sharing order data.",
        }
    return None


async def get_shipment_status(session: CallSession, order_id: str | None = None, supplier_phone: str | None = None) -> dict[str, Any]:
    """Get the identified caller's latest shipment for an order."""
    if denial := _sensitive_read_denial(session):
        return denial
    supplier_id = _knowledge_authorized_supplier_id(session)
    async with async_session_scope() as db:
        q = (
            select(Shipment)
            .join(Order, Shipment.order_id == Order.id)
            .where(
                Shipment.tenant_id == session.tenant_id,
                Order.tenant_id == session.tenant_id,
                Order.supplier_id == supplier_id,
            )
        )
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
    authorized_supplier_id = _pin_authorized_supplier_id(session)
    if authorized_supplier_id is None:
        log.warning(
            "security.tier2_blocked",
            call_id=session.call_id,
            tenant_id=session.tenant_id,
            supplier_id=session.supplier_id,
        )
        return {
            "ok": False,
            "error": "pin_required",
            "verified_pin": False,
            "message": "Tier 2 PIN verification is required before placing a purchase order. Please ask the caller for their 4–8 digit security PIN and call verify_pin.",
        }

    if not supplier_id:
        supplier_id = authorized_supplier_id
    if supplier_id != authorized_supplier_id:
        return {
            "ok": False,
            "error": "supplier_mismatch",
            "message": "A purchase order can only be created for the PIN-verified supplier.",
        }
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
        sup = (
            await db.execute(
                select(Supplier).where(
                    Supplier.tenant_id == session.tenant_id,
                    Supplier.id == supplier_id,
                )
            )
        ).scalars().first()
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
        tenant = await db.get(Tenant, session.tenant_id)
        crm_job_id: str | None = None
        if tenant is not None and tenant.webhook_url:
            crm_result = await enqueue_side_effect_async(
                db,
                tenant_id=session.tenant_id,
                effect_type=CRM_WEBHOOK_SYNC,
                aggregate_type="order",
                aggregate_id=order_id,
                idempotency_key=f"crm-order:{order_id}",
                trace_id=f"call:{session.call_id}",
            )
            crm_job_id = crm_result.job_id

    return {
        "ok": True,
        "order_id": order_id,
        "supplier_id": supplier_id,
        "supplier_name": sup.name,
        "items": validated,
        "total_qty": total_qty,
        "status": "pending",
        "crm_job_id": crm_job_id,
    }


async def verify_po(session: CallSession, order_id: str) -> dict[str, Any]:
    """Confirm that a PO exists in the tenant's records."""
    if denial := _sensitive_read_denial(session):
        return denial
    supplier_id = _knowledge_authorized_supplier_id(session)
    async with async_session_scope() as db:
        query = select(Order).where(
            Order.tenant_id == session.tenant_id,
            Order.supplier_id == supplier_id,
            Order.id == order_id,
        )
        o = (await db.execute(query)).scalars().first()
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


async def _resolve_order(db: Any, session: CallSession, order_id: str | None, customer_po_ref: str | None) -> Order | None:
    """Find an order by our ID or by the customer's own PO reference.

    Always scoped to the active tenant AND to the caller's own contact record —
    a verified caller from company A must never be able to read company B's
    order by guessing an ID.
    """
    supplier_id = _knowledge_authorized_supplier_id(session)
    if supplier_id is None:
        return None
    q = select(Order).where(
        Order.tenant_id == session.tenant_id,
        Order.supplier_id == supplier_id,
    )

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
    if denial := _sensitive_read_denial(session):
        return denial
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
    if denial := _sensitive_read_denial(session):
        return denial
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

    # Day 34 persists the local audit and typed durable intent in the same
    # transaction. The voice path never starts a Sheets task or waits on Google.
    # The separate worker can retry a committed intent after an API restart.
    sheet_job_id: str | None = None
    crm_job_id: str | None = None
    async with async_session_scope() as db:
        worksheet_log = WorksheetLog(
            tenant_id=session.tenant_id,
            worksheet_name=get_settings().google_sheet_tab,
            action_type="append",
            row_data_json=json.dumps(row, default=str),
        )
        db.add(worksheet_log)
        await db.flush()
        if get_sheets_client().is_configured():
            sheet_result = await enqueue_side_effect_async(
                db,
                tenant_id=session.tenant_id,
                effect_type=SHEETS_CALL_OUTCOME,
                aggregate_type="worksheet_log",
                aggregate_id=str(worksheet_log.id),
                idempotency_key=f"sheets-call:{worksheet_log.id}",
                trace_id=f"call:{session.call_id}",
            )
            sheet_job_id = sheet_result.job_id

        tenant = await db.get(Tenant, session.tenant_id)
        if tenant is not None and tenant.webhook_url:
            crm_result = await enqueue_side_effect_async(
                db,
                tenant_id=session.tenant_id,
                effect_type=CRM_WEBHOOK_SYNC,
                aggregate_type="worksheet_log",
                aggregate_id=str(worksheet_log.id),
                idempotency_key=f"crm-call-outcome:{worksheet_log.id}",
                trace_id=f"call:{session.call_id}",
            )
            crm_job_id = crm_result.job_id

    session.sheet_task = None
    session.sheet_synced = False

    log.info(
        "call.outcome_logged",
        call_id=session.call_id,
        resolution=resolution_status,
        satisfaction=satisfaction,
        sheet="queued" if sheet_job_id else "off",
        crm="queued" if crm_job_id else "off",
    )

    return {
        "ok": True,
        "logged": True,
        "resolution_status": resolution_status,
        "satisfaction": satisfaction,
        # "queued" tells the model a durable worker owns the mirror; it must
        # not claim Sheets has already accepted the row.
        "sheet_synced": "queued" if sheet_job_id else session.sheet_synced,
        "sheet_job_id": sheet_job_id,
        "crm_job_id": crm_job_id,
    }


async def schedule_appointment(session: CallSession, datetime_str: str, purpose: str = "") -> dict[str, Any]:
    """Schedule a supplier appointment for the authorized caller only."""
    # Same fail-closed posture as protected reads: an identified contact books
    # only for themselves, and only after proving who they are. Without this,
    # any caller could spam confirmed dock appointments against any supplier.
    supplier_id = _knowledge_authorized_supplier_id(session)
    if supplier_id is None:
        return {
            "ok": False,
            "error": "not_verified",
            "message": "Verify the caller before scheduling an appointment.",
        }
    app_id = f"app-{uuid.uuid4().hex[:6]}"
    if not datetime_str or not isinstance(datetime_str, str):
        return {"ok": False, "error": "invalid_datetime", "appointment_id": None}
    try:
        dt = datetime.fromisoformat(datetime_str.strip().replace("Z", "+00:00"))
    except Exception:
        return {"ok": False, "error": "invalid_datetime", "appointment_id": None}

    crm_job_id: str | None = None
    async with async_session_scope() as db:
        app = Appointment(
            id=app_id,
            tenant_id=session.tenant_id,
            supplier_id=supplier_id,
            datetime=dt,
            purpose=purpose,
            status="confirmed",
        )
        db.add(app)
        await db.flush()
        tenant = await db.get(Tenant, session.tenant_id)
        if tenant is not None and tenant.webhook_url:
            crm_result = await enqueue_side_effect_async(
                db,
                tenant_id=session.tenant_id,
                effect_type=CRM_WEBHOOK_SYNC,
                aggregate_type="appointment",
                aggregate_id=app_id,
                idempotency_key=f"crm-appointment:{app_id}",
                trace_id=f"call:{session.call_id}",
            )
            crm_job_id = crm_result.job_id

    return {
        "ok": True,
        "appointment_id": app_id,
        "datetime": dt.isoformat(),
        "purpose": purpose,
        "crm_job_id": crm_job_id,
    }


async def _queue_notification(
    session: CallSession,
    *,
    channel: str,
    recipient: str,
    subject: str | None,
    body: str,
) -> dict[str, Any]:
    """Persist notification intent and its worker-owned job in one transaction."""

    comm_id = f"comm-{channel}-{uuid.uuid4().hex[:20]}"
    async with async_session_scope() as db:
        db.add(
            CommunicationLog(
                id=comm_id,
                tenant_id=session.tenant_id,
                channel=channel,
                recipient=recipient,
                subject=subject,
                body=body,
                status="queued",
            )
        )
        enqueue_result = await enqueue_side_effect_async(
            db,
            tenant_id=session.tenant_id,
            effect_type=NOTIFICATION_DISPATCH,
            aggregate_type="communication_log",
            aggregate_id=comm_id,
            idempotency_key=f"notification:{comm_id}",
            trace_id=f"call:{session.call_id}",
        )
    log.info("notification.queued", channel=channel, comm_id=comm_id)
    return {
        "ok": True,
        "comm_id": comm_id,
        "channel": channel,
        "recipient": recipient,
        "status": "queued",
        "job_id": enqueue_result.job_id,
    }


async def send_email(session: CallSession, to_address: str, subject: str, body: str) -> dict[str, Any]:
    """Queue an email notification; a Day 34 worker owns any future transport."""

    return await _queue_notification(
        session,
        channel="email",
        recipient=to_address.strip(),
        subject=subject,
        body=body,
    )




async def send_whatsapp_message(session: CallSession, to_phone: str, message: str) -> dict[str, Any]:
    """Queue a WhatsApp notification; no Twilio request happens in a voice turn."""

    target = to_phone.strip()
    if not target.startswith("whatsapp:"):
        if not target.startswith("+"):
            target = f"+{target}"
        target = f"whatsapp:{target}"
    return await _queue_notification(
        session,
        channel="whatsapp",
        recipient=target,
        subject=None,
        body=message,
    )


async def send_sms(session: CallSession, to_phone: str, message: str) -> dict[str, Any]:
    """Queue an SMS notification; no Twilio request happens in a voice turn."""

    target = to_phone.strip()
    if not target.startswith("+"):
        target = f"+{target}"
    return await _queue_notification(
        session,
        channel="sms",
        recipient=target,
        subject=None,
        body=message,
    )


async def update_worksheet(session: CallSession, worksheet_name: str, action: str, row_data: dict[str, Any]) -> dict[str, Any]:
    """Append an ad-hoc row to a Google Sheets tab, plus a local audit entry.

    For the standard call-outcome row prefer `log_call_outcome` — it enforces
    the canonical column order. This tool is the escape hatch for anything else
    the ops team wants captured on a sheet.
    """
    # Guardrails: only append is ever executed, and worksheet names must be
    # sane. The model can hallucinate an "update"/"delete" action or a bogus
    # tab name; the local audit row would happily record it.
    if action != "append":
        return {"ok": False, "error": "unsupported_action", "message": "Only 'append' is supported."}
    if not isinstance(worksheet_name, str) or not worksheet_name.strip() or len(worksheet_name) > 100:
        return {"ok": False, "error": "invalid_worksheet"}
    if not isinstance(row_data, dict) or not row_data:
        return {"ok": False, "error": "invalid_row_data"}

    job_id: str | None = None
    async with async_session_scope() as db:
        worksheet_log = WorksheetLog(
            tenant_id=session.tenant_id,
            worksheet_name=worksheet_name,
            action_type=action,
            row_data_json=json.dumps(row_data, default=str),
        )
        db.add(worksheet_log)
        await db.flush()
        if action == "append" and row_data and get_sheets_client().is_configured():
            enqueue_result = await enqueue_side_effect_async(
                db,
                tenant_id=session.tenant_id,
                effect_type=SHEETS_WORKSHEET_APPEND,
                aggregate_type="worksheet_log",
                aggregate_id=str(worksheet_log.id),
                idempotency_key=f"sheets-worksheet:{worksheet_log.id}",
                trace_id=f"call:{session.call_id}",
            )
            job_id = enqueue_result.job_id

    return {
        "ok": True,
        "worksheet": worksheet_name,
        "action": action,
        "sheet_synced": "queued" if job_id else False,
        "job_id": job_id,
    }


async def edit_sheet_row(
    session: CallSession,
    worksheet_name: str,
    search_column: str,
    search_value: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Find a row in the workspace's Google Spreadsheet by key and update columns in place."""
    if not isinstance(worksheet_name, str) or not worksheet_name.strip() or len(worksheet_name) > 100:
        return {"ok": False, "error": "invalid_worksheet"}
    if not isinstance(search_column, str) or not search_column.strip() or len(search_column) > 64:
        return {"ok": False, "error": "invalid_search_column"}
    if not isinstance(search_value, str) or not search_value.strip() or len(search_value) > 128:
        return {"ok": False, "error": "invalid_search_value"}
    if not isinstance(updates, dict) or not updates:
        return {"ok": False, "error": "invalid_updates"}

    target_sheet_id: str | None = None
    async with async_session_scope() as db:
        tenant = await db.get(Tenant, session.tenant_id)
        if tenant and tenant.google_sheet_id:
            target_sheet_id = tenant.google_sheet_id

        worksheet_log = WorksheetLog(
            tenant_id=session.tenant_id,
            worksheet_name=worksheet_name,
            action_type="edit_row",
            row_data_json=json.dumps({
                "search_column": search_column,
                "search_value": search_value,
                "updates": updates,
            }, default=str),
        )
        db.add(worksheet_log)
        await db.flush()

    gsheets = get_sheets_client()
    if target_sheet_id or gsheets.is_configured():
        edit_result = await gsheets.update_row_by_key(
            match_column=search_column.strip(),
            match_value=search_value.strip(),
            update_values=updates,
            tab=worksheet_name.strip(),
            target_sheet_id=target_sheet_id,
        )
        return {
            "ok": edit_result.get("ok", False),
            "action": edit_result.get("action", "updated"),
            "worksheet": worksheet_name,
            "row_number": edit_result.get("row_number"),
            "updates": edit_result.get("updates", []),
            "detail": edit_result.get("detail", "Spreadsheet row updated successfully"),
        }

    return {
        "ok": True,
        "action": "logged_locally",
        "worksheet": worksheet_name,
        "message": "Row edit recorded in local workspace database.",
    }


async def type_notes(session: CallSession, text: str) -> dict[str, Any]:
    """Record free-form notes during a call."""
    log.info("notes.typed", text=text)
    return {"ok": True, "note": text}


async def escalate_to_human(session: CallSession, reason: str = "", summary: str = "") -> dict[str, Any]:
    """Flag a follow-up and durably queue any configured CRM escalation sync."""

    session.escalated = True
    session.intent = session.intent or "escalation"
    crm_job_id: str | None = None
    async with async_session_scope() as db:
        escalation_log = WorksheetLog(
            tenant_id=session.tenant_id,
            worksheet_name="Escalations",
            action_type="escalation",
            row_data_json=json.dumps(
                {
                    "call_id": session.call_id,
                    "reason": reason,
                    "summary": summary,
                },
                default=str,
            ),
        )
        db.add(escalation_log)
        await db.flush()
        tenant = await db.get(Tenant, session.tenant_id)
        if tenant is not None and tenant.webhook_url:
            crm_result = await enqueue_side_effect_async(
                db,
                tenant_id=session.tenant_id,
                effect_type=CRM_WEBHOOK_SYNC,
                aggregate_type="worksheet_log",
                aggregate_id=str(escalation_log.id),
                idempotency_key=f"crm-escalation:{escalation_log.id}",
                trace_id=f"call:{session.call_id}",
            )
            crm_job_id = crm_result.job_id
    log.info("agent.escalate", call_id=session.call_id, reason=reason, crm="queued" if crm_job_id else "off")
    return {
        "ok": True,
        "call_id": session.call_id,
        "reason": reason,
        "summary": summary,
        "crm_job_id": crm_job_id,
    }


async def place_outbound_call(session: CallSession, to_phone: str, instruction: str) -> dict[str, Any]:
    """Reject direct provider calls; campaign jobs are the only durable path."""

    log.warning("outbound_call.rejected_direct_tool", tenant_id=session.tenant_id, call_id=session.call_id)
    return {
        "ok": False,
        "error": "direct_outbound_calls_disabled",
        "message": "Use an approved durable campaign target; this tool never invokes a provider directly.",
    }


# ---------- Dispatcher ----------


async def execute_tool(name: str, args: dict[str, Any], session: CallSession) -> dict[str, Any]:
    try:
        if name == "lookup_supplier":
            return await lookup_supplier(session, **(args or {}))
        if name == "verify_caller":
            return await verify_caller(session, **(args or {}))
        if name == "verify_pin":
            return await verify_pin(session, **(args or {}))
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
        if name == "send_sms":
            return await send_sms(session, **(args or {}))
        if name == "place_outbound_call":
            return await place_outbound_call(session, **(args or {}))
        if name == "update_worksheet":
            return await update_worksheet(session, **(args or {}))
        if name == "edit_sheet_row":
            return await edit_sheet_row(session, **(args or {}))
        if name == "type_notes":
            return await type_notes(session, **(args or {}))
        if name == "escalate_to_human":
            return await escalate_to_human(session, **(args or {}))
        return {"ok": False, "error": f"unknown_tool:{name}"}
    except Exception as e:
        # Never leak internal error text (stack fragments, SQL, provider keys)
        # into the model's context — it can be echoed back to the caller.
        log.error("tool.error", name=name, error=redact_pin_text(str(e)))
        return {
            "ok": False,
            "error": "internal_tool_error",
            "tool": name,
            "message": "The request could not be completed. Please try again in a moment.",
        }


# ---------- Dynamic tool gating (Day 54: sub-400ms) ----------

# Pre-computed token tax: TOOL_DEFINITIONS is 8180 chars ≈2045 tokens of fixed
# prefix on every LLM iteration (up to 5). No turn needs all 22 tools.
# Gating drops the prefix by ~60% before verification and ~30% after.

_CORE_TOOLS: frozenset[str] = frozenset({
    "lookup_supplier", "verify_caller", "verify_pin", "check_stock", "type_notes", "escalate_to_human",
})

_VERIFIED_READ_TOOLS: frozenset[str] = frozenset({
    "get_shipment_status", "verify_po", "check_po_status", "get_order_details",
})

# Writes that need at least knowledge verification (schedule) or PIN (create_po).
_VERIFIED_WRITE_TOOLS: frozenset[str] = frozenset({
    "schedule_appointment", "log_call_outcome",
})
_PIN_WRITE_TOOLS: frozenset[str] = frozenset({"create_po"})

# Messaging / sheets only after a verified contact exists — otherwise the
# model burns tokens on tools it cannot usefully call yet.
_POST_VERIFY_TOOLS: frozenset[str] = frozenset({
    "send_email", "send_whatsapp_message", "send_sms", "update_worksheet", "edit_sheet_row",
})


def tool_definitions_for(session: Any | None) -> list[dict[str, Any]]:
    """Return the minimal tool set for this session's verification state.

    Keeps the full 22-tool list for `pin_verified` sessions (no surprise
    hiding once fully authorized). Filters aggressively before verification to
    cut ~1.5k input tokens per LLM call on the free tier.
    """

    if session is None:
        return TOOL_DEFINITIONS
    # Session may be a CallSession or a test stub — be permissive.
    verified = bool(getattr(session, "verified", False))
    # Knowledge binding is the true gate — session.verified alone can desync
    # if the identified contact changed. Check the bound ID when available.
    try:
        has_knowledge = _knowledge_authorized_supplier_id(session) is not None  # type: ignore[arg-type]
    except Exception:
        has_knowledge = verified
    try:
        has_pin = _pin_authorized_supplier_id(session) is not None  # type: ignore[arg-type]
    except Exception:
        has_pin = bool(getattr(session, "pin_verified", False))

    if not verified or not has_knowledge:
        allowed = _CORE_TOOLS
    elif not has_pin:
        allowed = _CORE_TOOLS | _VERIFIED_READ_TOOLS | _VERIFIED_WRITE_TOOLS | _POST_VERIFY_TOOLS
    else:
        return TOOL_DEFINITIONS

    # Preserve original ordering so prompt-cache prefix stays stable.
    return [t for t in TOOL_DEFINITIONS if t.get("function", {}).get("name") in allowed]


def gated_tool_count(session: Any | None) -> int:
    """How many tool schemas will be sent for this session (for logging/benchmarks)."""

    return len(tool_definitions_for(session))


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
            "name": "verify_pin",
            "description": "Verify the caller's 4–8 digit security PIN before protected reads in enhanced mode or any protected write.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pin": {
                        "type": "string",
                        "description": "The 4–8 digit security PIN provided by the caller.",
                    },
                },
                "required": ["pin"],
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
            "description": "Get the verified caller's latest shipment status for a PO.",
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
            "description": "Verify a PO for the knowledge-verified caller.",
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
            "name": "send_sms",
            "description": "Send an SMS text message to the caller/supplier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_phone": {"type": "string", "description": "Recipient phone number in E.164 format"},
                    "message": {"type": "string", "description": "Text message content to send via SMS"},
                },
                "required": ["to_phone", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "place_outbound_call",
            "description": "Place an autonomous outbound AI voice call to a supplier, distributor, or customer for urgent updates, delayed deliveries, or order notifications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_phone": {"type": "string", "description": "Recipient phone number in E.164 format, e.g. +919876543210"},
                    "instruction": {"type": "string", "description": "Specific instruction/context for what the voice agent must explain to the person on the call"},
                },
                "required": ["to_phone", "instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_worksheet",
            "description": "Log or append an entry in a spreadsheet worksheet.",
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
            "name": "edit_sheet_row",
            "description": "Find an existing row in a spreadsheet tab by key (e.g. PO number, Order ID, or Supplier Name) and update column values in place.",
            "parameters": {
                "type": "object",
                "properties": {
                    "worksheet_name": {"type": "string", "description": "Tab name on the Google Spreadsheet (e.g. 'Orders', 'Deliveries', 'Call Log')"},
                    "search_column": {"type": "string", "description": "Header column name to search (e.g. 'PO Number', 'Order ID', 'Supplier')"},
                    "search_value": {"type": "string", "description": "Value to match (e.g. 'PO-1002', 'Varun Beverages')"},
                    "updates": {"type": "object", "description": "Dictionary of column names to updated values (e.g. {'Status': 'Confirmed', 'ETA': 'Tomorrow 10 AM'})"},
                },
                "required": ["worksheet_name", "search_column", "search_value", "updates"],
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
