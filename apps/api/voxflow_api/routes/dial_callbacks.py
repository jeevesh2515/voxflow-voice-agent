"""Day 33 Dial sandbox webhook ingress and controlled reconciliation handoff."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_session
from ..integrations.dial_callbacks import (
    DialCallbackError,
    dial_callback_allowed_tenant_ids,
    verify_and_normalise_dial_callback,
)
from ..jobs.provider_adapter_audits import (
    provider_operation_tenant_id,
    record_provider_adapter_audit,
)
from ..jobs.provider_events import apply_provider_callback


router = APIRouter(prefix="/api/provider-callbacks/dial", tags=["dial-callbacks"])


def _payload_hash(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def _error_audit_required(code: str) -> bool:
    """Disabled or unconfigured ingress remains invisible and mutation-free."""

    return code not in {
        "dial_callback_adapter_disabled",
        "dial_callback_sandbox_mode_required",
        "dial_callback_not_configured",
    }


@router.post("/events")
async def dial_callback_event(
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, str | bool | None]:
    """Verify and normalize one Dial sandbox webhook without trusting callback identity.

    The route does not create subscriptions or provider calls. It accepts an event
    only while the adapter is explicitly enabled in sandbox mode and a signing
    secret has been configured. Normalized callbacks are applied only to an
    existing outbound provider operation for an allow-listed tenant.
    """

    raw_body = await request.body()
    payload_hash = _payload_hash(raw_body)
    try:
        parsed = verify_and_normalise_dial_callback(request, raw_body)
    except DialCallbackError as exc:
        if _error_audit_required(exc.code):
            try:
                record_provider_adapter_audit(
                    db,
                    provider="dial",
                    provider_event_id=exc.provider_event_id,
                    provider_event_type=exc.provider_event_type,
                    payload_hash=payload_hash,
                    verification_status="rejected",
                    normalization_status="not_normalized",
                    application_status="rejected",
                    reason_code=exc.code,
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

    if parsed.disposition == "ping":
        record_provider_adapter_audit(
            db,
            provider="dial",
            provider_event_id=parsed.provider_event_id,
            provider_event_type=parsed.provider_event_type,
            payload_hash=payload_hash,
            verification_status="verified",
            normalization_status="ping",
            application_status="acknowledged",
        )
        db.commit()
        return {"ok": True, "state": "ping_acknowledged", "apply_status": "not_applicable", "anomaly_code": None}

    if parsed.disposition == "ignored":
        record_provider_adapter_audit(
            db,
            provider="dial",
            provider_event_id=parsed.provider_event_id,
            provider_event_type=parsed.provider_event_type,
            payload_hash=payload_hash,
            verification_status="verified",
            normalization_status="ignored",
            application_status="acknowledged",
            reason_code=parsed.reason_code,
        )
        db.commit()
        return {"ok": True, "state": "acknowledged", "apply_status": "not_applicable", "anomaly_code": parsed.reason_code}

    normalized = parsed.normalized
    assert normalized is not None  # guarded by the adapter's immutable result shape
    resolved_tenant_id = provider_operation_tenant_id(
        db,
        provider="dial",
        provider_call_id=normalized.provider_call_id,
    )
    allowed_tenants = dial_callback_allowed_tenant_ids()
    if resolved_tenant_id is not None and resolved_tenant_id not in allowed_tenants:
        record_provider_adapter_audit(
            db,
            provider="dial",
            provider_event_id=normalized.provider_event_id,
            provider_event_type=parsed.provider_event_type,
            payload_hash=payload_hash,
            verification_status="verified",
            normalization_status="normalized",
            application_status="blocked_tenant",
            reason_code="dial_callback_tenant_not_allowed",
            tenant_id=resolved_tenant_id,
        )
        db.commit()
        return {
            "ok": True,
            "state": "blocked",
            "apply_status": "blocked_tenant",
            "anomaly_code": "dial_callback_tenant_not_allowed",
        }

    try:
        result = apply_provider_callback(
            db,
            provider="dial",
            provider_event_id=normalized.provider_event_id,
            provider_call_id=normalized.provider_call_id,
            event_type=normalized.event_type,
            occurred_at=normalized.occurred_at,
            outcome=normalized.outcome,
            payload_hash=payload_hash,
        )
        record_provider_adapter_audit(
            db,
            provider="dial",
            provider_event_id=normalized.provider_event_id,
            provider_event_type=parsed.provider_event_type,
            payload_hash=payload_hash,
            verification_status="verified",
            normalization_status="normalized",
            application_status=result.apply_status,
            reason_code=result.anomaly_code,
            tenant_id=result.tenant_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "ok": True,
        "state": result.state,
        "apply_status": result.apply_status,
        "anomaly_code": result.anomaly_code,
    }
