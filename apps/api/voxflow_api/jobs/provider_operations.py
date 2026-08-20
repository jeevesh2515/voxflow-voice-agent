"""Durable provider-operation idempotency and reconciliation primitives."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import ProviderOperation
from .repository import utcnow


@dataclass(frozen=True)
class ProviderOperationResult:
    """Provider-operation state returned to campaign dispatch handlers."""

    id: str
    status: str
    provider_id: str | None
    created: bool


def _existing_operation(
    db: Session,
    *,
    tenant_id: str,
    provider: str,
    operation_type: str,
    idempotency_key: str,
) -> ProviderOperation | None:
    return (
        db.query(ProviderOperation)
        .filter(
            ProviderOperation.tenant_id == tenant_id,
            ProviderOperation.provider == provider,
            ProviderOperation.operation_type == operation_type,
            ProviderOperation.idempotency_key == idempotency_key,
        )
        .one_or_none()
    )


def reserve_provider_operation(
    db: Session,
    *,
    tenant_id: str,
    provider: str,
    operation_type: str,
    idempotency_key: str,
    request_hash: str,
    now: datetime | None = None,
) -> ProviderOperationResult:
    """Return the durable provider-operation record for one external intent.

    A unique tenant/provider/operation/idempotency tuple prevents a retry from
    treating the same outbound call request as a new external side effect.
    """

    existing = _existing_operation(
        db,
        tenant_id=tenant_id,
        provider=provider,
        operation_type=operation_type,
        idempotency_key=idempotency_key,
    )
    if existing:
        return ProviderOperationResult(existing.id, existing.status, existing.provider_id, False)

    operation_id = f"pop-{uuid.uuid4().hex[:20]}"
    requested_at = now or utcnow()
    try:
        with db.begin_nested():
            db.add(
                ProviderOperation(
                    id=operation_id,
                    tenant_id=tenant_id,
                    provider=provider,
                    operation_type=operation_type,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    status="requested",
                    requested_at=requested_at,
                    updated_at=requested_at,
                )
            )
            db.flush()
    except IntegrityError:
        db.expire_all()
        existing = _existing_operation(
            db,
            tenant_id=tenant_id,
            provider=provider,
            operation_type=operation_type,
            idempotency_key=idempotency_key,
        )
        if existing:
            return ProviderOperationResult(existing.id, existing.status, existing.provider_id, False)
        raise
    return ProviderOperationResult(operation_id, "requested", None, True)


def update_provider_operation(
    db: Session,
    *,
    operation_id: str,
    status: str,
    provider_id: str | None = None,
    now: datetime | None = None,
) -> None:
    """Persist a reconciled provider state without changing its idempotency key."""

    operation = db.get(ProviderOperation, operation_id)
    if operation is None:
        raise LookupError(f"provider operation {operation_id!r} does not exist")
    operation.status = status
    if provider_id:
        operation.provider_id = provider_id
    if status in {"confirmed", "dry_run"}:
        operation.confirmed_at = now or utcnow()
    operation.updated_at = now or utcnow()
    db.flush()
