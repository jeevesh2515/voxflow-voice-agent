"""Redacted Day 33 audit helpers for provider-specific callback adapters."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..db import ProviderCallbackAdapterAudit, ProviderOperation


def provider_operation_tenant_id(db: Session, *, provider: str, provider_call_id: str) -> str | None:
    """Resolve a tenant only from one stored outbound provider operation."""

    operations = (
        db.query(ProviderOperation)
        .filter(
            ProviderOperation.provider == provider,
            ProviderOperation.provider_id == provider_call_id,
        )
        .limit(2)
        .all()
    )
    if len(operations) != 1 or operations[0].operation_type != "outbound_call":
        return None
    return operations[0].tenant_id


def record_provider_adapter_audit(
    db: Session,
    *,
    provider: str,
    provider_event_id: str | None,
    provider_event_type: str | None,
    payload_hash: str,
    verification_status: str,
    normalization_status: str,
    application_status: str,
    reason_code: str | None = None,
    tenant_id: str | None = None,
    now: datetime | None = None,
) -> ProviderCallbackAdapterAudit:
    """Persist one non-sensitive adapter receipt, idempotent by payload identity.

    The caller supplies a cryptographic payload hash rather than raw callback
    content. Missing provider IDs use a hash-derived opaque receipt key, enabling
    observability for malformed/forged traffic without retaining the request.
    """

    effective_event_id = (provider_event_id or f"unidentified-{payload_hash[:32]}")[:128]
    existing = (
        db.query(ProviderCallbackAdapterAudit)
        .filter(
            ProviderCallbackAdapterAudit.provider == provider,
            ProviderCallbackAdapterAudit.provider_event_id == effective_event_id,
            ProviderCallbackAdapterAudit.payload_hash == payload_hash,
        )
        .one_or_none()
    )
    if existing is not None:
        return existing

    created_at = now or datetime.now(timezone.utc)
    audit = ProviderCallbackAdapterAudit(
        id=f"pca-{uuid.uuid4().hex[:20]}",
        tenant_id=tenant_id,
        provider=provider,
        provider_event_id=effective_event_id,
        provider_event_type=provider_event_type,
        payload_hash=payload_hash,
        verification_status=verification_status,
        normalization_status=normalization_status,
        application_status=application_status,
        reason_code=reason_code,
        created_at=created_at,
    )
    db.add(audit)
    db.flush()
    return audit
