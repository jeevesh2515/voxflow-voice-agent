"""GDPR privacy domain services — DSAR export, erasure, PII masking."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..db import Call, CommunicationLog, Supplier

# ponytail: stdlib masking, no external lib


def mask_phone_number(phone: str) -> str:
    """Mask middle digits: +44 7911 123456 -> +44 7911 *** 456."""
    if not phone or not phone.strip():
        return phone
    p = phone.strip()
    digits = "".join(c for c in p if c.isdigit())
    if len(digits) <= 4:
        return "***"
    # ponytail: rsplit keeps prefix intact, no regex drift
    if " " in p:
        prefix, last_block = p.rsplit(" ", 1)
        # last_block should be digits; if not, fallback to generic
        block_digits = "".join(c for c in last_block if c.isdigit())
        if block_digits and len(block_digits) >= 3:
            return f"{prefix} *** {block_digits[-3:]}"
    if len(p) > 6:
        return f"{p[:-6].rstrip()} *** {p[-3:]}"
    return f"*** {p[-3:]}"


def mask_phone_number_simple(phone: str) -> str:
    if not phone or not phone.strip():
        return phone
    return mask_phone_number(phone)


def mask_email_address(email: str) -> str:
    """john.doe@acme.co.uk -> j***e@acme.co.uk"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***" if local else "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"


def _normalize_search(value: str) -> str:
    return value.strip().lower()


def _matches_subject(value: str, search: str) -> bool:
    return _normalize_search(value) == _normalize_search(search)


def export_data_subject(db: Session, tenant_id: str, search_phone_or_email: str) -> dict[str, Any]:
    """GDPR Right of Access — bundle all data matching caller phone/email."""
    search = search_phone_or_email.strip()
    if not search:
        return {"tenant_id": tenant_id, "subject": search_phone_or_email, "records": {}}
    search_norm = _normalize_search(search)

    # Calls matching phone or name-email? We match caller_phone exact or caller_name/email
    calls = db.query(Call).filter(Call.tenant_id == tenant_id).all()
    matched_calls = [
        c for c in calls if _normalize_search(c.caller_phone) == search_norm or _normalize_search(c.caller_name) == search_norm
    ]

    suppliers = db.query(Supplier).filter(Supplier.tenant_id == tenant_id).all()
    matched_suppliers = [
        s for s in suppliers if _normalize_search(s.phone) == search_norm or _normalize_search(s.contact_person) == search_norm or _normalize_search(s.name) == search_norm
    ]
    # Also check email in suppliers? No email field; use phone match
    # Communication logs matching recipient
    comms = db.query(CommunicationLog).filter(CommunicationLog.tenant_id == tenant_id).all()
    matched_comms = [c for c in comms if _normalize_search(c.recipient) == search_norm]

    # Escalations are part of calls with escalation_status != none
    escalations = [c for c in matched_calls if getattr(c, "escalation_status", "none") != "none" or c.escalated]

    def call_payload(c: Call) -> dict[str, Any]:
        try:
            transcript = json.loads(c.transcript_json) if c.transcript_json else []
        except Exception:
            transcript = []
        return {
            "id": c.id,
            "caller_phone": c.caller_phone,
            "caller_name": c.caller_name,
            "language": c.language,
            "intent": c.intent,
            "outcome": c.outcome,
            "transcript": transcript,
            "recording_url": c.recording_url,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "escalation_status": getattr(c, "escalation_status", None),
        }

    return {
        "tenant_id": tenant_id,
        "subject": search,
        "records": {
            "suppliers": [{"id": s.id, "name": s.name, "phone": s.phone, "contact_person": s.contact_person} for s in matched_suppliers],
            "calls": [call_payload(c) for c in matched_calls],
            "escalations": [call_payload(c) for c in escalations],
            "communication_logs": [
                {"id": c.id, "channel": c.channel, "recipient": c.recipient, "subject": c.subject, "timestamp": c.timestamp.isoformat() if c.timestamp else None}
                for c in matched_comms
            ],
            "transcripts": [{"call_id": c.id, "transcript_json": c.transcript_json} for c in matched_calls],
            "audio_references": [{"call_id": c.id, "recording_url": c.recording_url} for c in matched_calls if c.recording_url],
        },
        "counts": {
            "suppliers": len(matched_suppliers),
            "calls": len(matched_calls),
            "escalations": len(escalations),
            "communication_logs": len(matched_comms),
        },
    }


def erase_data_subject(db: Session, tenant_id: str, search_phone_or_email: str, erased_by_user_id: str) -> dict[str, Any]:
    """GDPR Right to be Forgotten — anonymize PII preserving order refs."""
    search = search_phone_or_email.strip()
    search_norm = _normalize_search(search)
    if not search:
        return {"tenant_id": tenant_id, "subject": search_phone_or_email, "anonymized_calls": 0, "anonymized_comms": 0, "anonymized_suppliers": 0}

    calls = db.query(Call).filter(Call.tenant_id == tenant_id).all()
    matched_calls = [c for c in calls if _normalize_search(c.caller_phone) == search_norm or _normalize_search(c.caller_name) == search_norm]
    comms = db.query(CommunicationLog).filter(CommunicationLog.tenant_id == tenant_id).all()
    matched_comms = [c for c in comms if _normalize_search(c.recipient) == search_norm]
    suppliers = db.query(Supplier).filter(Supplier.tenant_id == tenant_id).all()
    matched_suppliers = [s for s in suppliers if _normalize_search(s.phone) == search_norm]

    for c in matched_calls:
        c.caller_name = "REDACTED"
        # mask phone deterministically: keep country/prefix, mask middle, keep last 3
        if c.caller_phone:
            c.caller_phone = mask_phone_number(c.caller_phone) if c.caller_phone.strip() else "REDACTED"
            # If masking produced same value for generic, ensure anonymized
            if _normalize_search(c.caller_phone) == search_norm:
                c.caller_phone = "REDACTED"
        c.transcript_json = "[]"
        c.transcript_json = "[]"
        # wipe transcript-related fields but keep order refs (notes etc. stay)
        c.reason = ""
        c.solution = ""
        c.staff_resolution = ""
        # recording reference wiped
        c.recording_url = None

    for comm in matched_comms:
        comm.recipient = mask_email_address(comm.recipient) if "@" in comm.recipient else mask_phone_number(comm.recipient)
        comm.body = "[REDACTED]"
        if comm.subject:
            comm.subject = "[REDACTED]"

    for s in matched_suppliers:
        s.phone = mask_phone_number(s.phone)
        s.contact_person = "REDACTED"
        s.name = s.name  # keep supplier name? spec says supplier notes anonymized but financial refs preserved; keep name but could mask? Keep as is for accounting invariants, only PII contact masked

    db.flush()
    return {
        "tenant_id": tenant_id,
        "subject": search,
        "erased_by": erased_by_user_id,
        "anonymized_calls": len(matched_calls),
        "anonymized_communications": len(matched_comms),
        "anonymized_suppliers": len(matched_suppliers),
        "erased_at": datetime.now(timezone.utc).isoformat(),
    }
