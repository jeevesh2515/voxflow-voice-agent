"""Signed Day 32 provider callback ingestion for durable campaign lifecycle reconciliation."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_session
from ..jobs.provider_events import apply_provider_callback

router = APIRouter(prefix="/api/provider-callbacks", tags=["provider-callbacks"])


class ProviderCallbackIn(BaseModel):
    """Normalized callback shape accepted after signature verification.

    Deliberately does not contain a tenant, campaign, queue, or job identifier.
    The callback can affect a tenant only by resolving its provider/call pair to
    an existing durable ProviderOperation.
    """

    provider: Literal["dial"]
    event_id: str = Field(min_length=1, max_length=128)
    call_id: str = Field(min_length=1, max_length=128)
    event_type: Literal[
        "request_accepted",
        "connected",
        "ended",
        "recording_ready",
        "business_outcome",
    ]
    occurred_at: datetime
    outcome: str | None = Field(default=None, max_length=64)


def _signature_message(timestamp: str, body: bytes) -> bytes:
    return timestamp.encode("ascii") + b"." + body


def _verify_callback_signature(request: Request, body: bytes) -> None:
    """Reject unsigned, stale, malformed, or mismatched provider callbacks."""

    settings = get_settings()
    if not settings.provider_callback_validate_signature:
        return
    if not settings.provider_callback_shared_secret:
        raise HTTPException(status_code=503, detail="provider_callback_not_configured")

    timestamp = request.headers.get("X-VoxFlow-Timestamp", "")
    signature = request.headers.get("X-VoxFlow-Signature", "")
    try:
        sent_at = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="invalid_callback_timestamp") from exc
    if not signature:
        raise HTTPException(status_code=403, detail="missing_callback_signature")

    now = int(datetime.now(timezone.utc).timestamp())
    if abs(now - sent_at) > settings.provider_callback_max_age_seconds:
        raise HTTPException(status_code=403, detail="stale_callback_timestamp")

    expected = hmac.new(
        settings.provider_callback_shared_secret.encode("utf-8"),
        _signature_message(timestamp, body),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="invalid_callback_signature")


@router.post("/events")
async def provider_callback_event(
    request: Request,
    payload: ProviderCallbackIn,
    db: Session = Depends(get_session),
) -> dict[str, str | None | bool]:
    """Store and apply one signed provider event without trusting caller tenant fields."""

    body = await request.body()
    _verify_callback_signature(request, body)
    payload_hash = hashlib.sha256(body).hexdigest()
    try:
        result = apply_provider_callback(
            db,
            provider=payload.provider,
            provider_event_id=payload.event_id,
            provider_call_id=payload.call_id,
            event_type=payload.event_type,
            occurred_at=payload.occurred_at,
            outcome=payload.outcome,
            payload_hash=payload_hash,
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
