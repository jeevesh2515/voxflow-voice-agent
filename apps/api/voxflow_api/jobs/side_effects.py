"""Day 34 typed durable side-effect intent ledger and enqueue primitives.

The API request path persists a trusted aggregate/audit row, the SideEffectIntent,
JobRun, and JobOutbox in one transaction. It never invokes Sheets, CRM webhooks,
Twilio, Gmail, recording storage, or a provider inline.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..db import JobOutbox, JobRun, SideEffectIntent

# The worker registration is explicit. A generic job type is intentionally not
# accepted so an unreviewed intent cannot turn into executable side-effect code.
SHEETS_CALL_OUTCOME = "sheets.call_outcome.append"
SHEETS_EMAIL_SUMMARY = "sheets.email_summary.append"
SHEETS_WORKSHEET_APPEND = "sheets.worksheet.append"
EMAIL_SUMMARIZATION_SCAN = "email.summarization.scan"
CRM_WEBHOOK_SYNC = "crm.webhook.sync"
NOTIFICATION_DISPATCH = "notification.dispatch"
RECORDING_RETRIEVE = "recording.retrieve"

SIDE_EFFECT_JOB_TYPES = (
    SHEETS_CALL_OUTCOME,
    SHEETS_EMAIL_SUMMARY,
    SHEETS_WORKSHEET_APPEND,
    EMAIL_SUMMARIZATION_SCAN,
    CRM_WEBHOOK_SYNC,
    NOTIFICATION_DISPATCH,
    RECORDING_RETRIEVE,
)


@dataclass(frozen=True)
class SideEffectEnqueueResult:
    """The one durable owner for a typed external-operation intent."""

    intent_id: str
    job_id: str
    outbox_id: str
    created: bool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _payload_hash(
    *,
    tenant_id: str,
    effect_type: str,
    aggregate_type: str,
    aggregate_id: str,
    idempotency_key: str,
) -> str:
    """Hash only bounded identifiers, never a sensitive operation payload."""

    material = {
        "aggregate_id": aggregate_id,
        "aggregate_type": aggregate_type,
        "effect_type": effect_type,
        "idempotency_key": idempotency_key,
        "tenant_id": tenant_id,
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _validate(
    *,
    tenant_id: str,
    effect_type: str,
    aggregate_type: str,
    aggregate_id: str,
    idempotency_key: str,
) -> None:
    if effect_type not in SIDE_EFFECT_JOB_TYPES:
        raise ValueError(f"unsupported side-effect job type: {effect_type}")
    for label, value, maximum in (
        ("tenant_id", tenant_id, 64),
        ("aggregate_type", aggregate_type, 128),
        ("aggregate_id", aggregate_id, 64),
        ("idempotency_key", idempotency_key, 255),
    ):
        if not value or not value.strip() or len(value) > maximum:
            raise ValueError(f"invalid {label}")


def _existing_sync(db: Session, *, tenant_id: str, idempotency_key: str) -> SideEffectEnqueueResult | None:
    intent = (
        db.query(SideEffectIntent)
        .filter(
            SideEffectIntent.tenant_id == tenant_id,
            SideEffectIntent.idempotency_key == idempotency_key,
        )
        .one_or_none()
    )
    if intent is None:
        return None
    job = db.get(JobRun, intent.job_id)
    outbox = (
        db.query(JobOutbox)
        .filter(JobOutbox.tenant_id == tenant_id, JobOutbox.idempotency_key == idempotency_key)
        .one_or_none()
    )
    if job is None or outbox is None:
        raise RuntimeError(f"side-effect durable pair is incomplete for {idempotency_key!r}")
    return SideEffectEnqueueResult(intent.id, job.id, outbox.id, False)


async def _existing_async(
    db: AsyncSession,
    *,
    tenant_id: str,
    idempotency_key: str,
) -> SideEffectEnqueueResult | None:
    intent = (
        await db.execute(
            select(SideEffectIntent).where(
                SideEffectIntent.tenant_id == tenant_id,
                SideEffectIntent.idempotency_key == idempotency_key,
            )
        )
    ).scalars().one_or_none()
    if intent is None:
        return None
    job = await db.get(JobRun, intent.job_id)
    outbox = (
        await db.execute(
            select(JobOutbox).where(
                JobOutbox.tenant_id == tenant_id,
                JobOutbox.idempotency_key == idempotency_key,
            )
        )
    ).scalars().one_or_none()
    if job is None or outbox is None:
        raise RuntimeError(f"side-effect durable pair is incomplete for {idempotency_key!r}")
    return SideEffectEnqueueResult(intent.id, job.id, outbox.id, False)


def enqueue_side_effect(
    db: Session,
    *,
    tenant_id: str,
    effect_type: str,
    aggregate_type: str,
    aggregate_id: str,
    idempotency_key: str,
    priority: int = 0,
    max_attempts: int = 6,
    trace_id: str | None = None,
) -> SideEffectEnqueueResult:
    """Atomically enqueue a typed side effect using an existing sync transaction."""

    _validate(
        tenant_id=tenant_id,
        effect_type=effect_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        idempotency_key=idempotency_key,
    )
    existing = _existing_sync(db, tenant_id=tenant_id, idempotency_key=idempotency_key)
    if existing:
        return existing

    intent_id = f"sei-{uuid.uuid4().hex[:20]}"
    job_id = f"job-{uuid.uuid4().hex[:20]}"
    outbox_id = f"out-{uuid.uuid4().hex[:20]}"
    payload_json = json.dumps({"side_effect_intent_id": intent_id}, sort_keys=True, separators=(",", ":"))
    now = utcnow()

    try:
        with db.begin_nested():
            db.add(
                JobRun(
                    id=job_id,
                    tenant_id=tenant_id,
                    job_type=effect_type,
                    payload_json=payload_json,
                    status="ready",
                    priority=priority,
                    idempotency_key=idempotency_key,
                    max_attempts=max_attempts,
                    trace_id=trace_id,
                    scheduled_at=now,
                    next_run_at=now,
                )
            )
            db.add(
                SideEffectIntent(
                    id=intent_id,
                    tenant_id=tenant_id,
                    job_id=job_id,
                    effect_type=effect_type,
                    aggregate_type=aggregate_type,
                    aggregate_id=aggregate_id,
                    idempotency_key=idempotency_key,
                    payload_hash=_payload_hash(
                        tenant_id=tenant_id,
                        effect_type=effect_type,
                        aggregate_type=aggregate_type,
                        aggregate_id=aggregate_id,
                        idempotency_key=idempotency_key,
                    ),
                    status="queued",
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                JobOutbox(
                    id=outbox_id,
                    tenant_id=tenant_id,
                    event_type=f"{effect_type}.queued",
                    aggregate_type=aggregate_type,
                    aggregate_id=aggregate_id,
                    payload_json=payload_json,
                    idempotency_key=idempotency_key,
                )
            )
            db.flush()
    except IntegrityError:
        db.expire_all()
        existing = _existing_sync(db, tenant_id=tenant_id, idempotency_key=idempotency_key)
        if existing:
            return existing
        raise

    return SideEffectEnqueueResult(intent_id, job_id, outbox_id, True)


async def enqueue_side_effect_async(
    db: AsyncSession,
    *,
    tenant_id: str,
    effect_type: str,
    aggregate_type: str,
    aggregate_id: str,
    idempotency_key: str,
    priority: int = 0,
    max_attempts: int = 6,
    trace_id: str | None = None,
) -> SideEffectEnqueueResult:
    """Async equivalent for agent/webhook transactions using ``AsyncSession``.

    The caller owns the surrounding `async_session_scope`, so an audit/domain row
    and its durable intent are committed or rolled back together.
    """

    _validate(
        tenant_id=tenant_id,
        effect_type=effect_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        idempotency_key=idempotency_key,
    )
    existing = await _existing_async(db, tenant_id=tenant_id, idempotency_key=idempotency_key)
    if existing:
        return existing

    intent_id = f"sei-{uuid.uuid4().hex[:20]}"
    job_id = f"job-{uuid.uuid4().hex[:20]}"
    outbox_id = f"out-{uuid.uuid4().hex[:20]}"
    payload_json = json.dumps({"side_effect_intent_id": intent_id}, sort_keys=True, separators=(",", ":"))
    now = utcnow()

    try:
        async with db.begin_nested():
            db.add(
                JobRun(
                    id=job_id,
                    tenant_id=tenant_id,
                    job_type=effect_type,
                    payload_json=payload_json,
                    status="ready",
                    priority=priority,
                    idempotency_key=idempotency_key,
                    max_attempts=max_attempts,
                    trace_id=trace_id,
                    scheduled_at=now,
                    next_run_at=now,
                )
            )
            db.add(
                SideEffectIntent(
                    id=intent_id,
                    tenant_id=tenant_id,
                    job_id=job_id,
                    effect_type=effect_type,
                    aggregate_type=aggregate_type,
                    aggregate_id=aggregate_id,
                    idempotency_key=idempotency_key,
                    payload_hash=_payload_hash(
                        tenant_id=tenant_id,
                        effect_type=effect_type,
                        aggregate_type=aggregate_type,
                        aggregate_id=aggregate_id,
                        idempotency_key=idempotency_key,
                    ),
                    status="queued",
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                JobOutbox(
                    id=outbox_id,
                    tenant_id=tenant_id,
                    event_type=f"{effect_type}.queued",
                    aggregate_type=aggregate_type,
                    aggregate_id=aggregate_id,
                    payload_json=payload_json,
                    idempotency_key=idempotency_key,
                )
            )
            await db.flush()
    except IntegrityError:
        # The savepoint keeps the outer domain transaction usable. Reloading the
        # winner makes concurrent enqueue requests idempotent instead of noisy.
        existing = await _existing_async(db, tenant_id=tenant_id, idempotency_key=idempotency_key)
        if existing:
            return existing
        raise

    return SideEffectEnqueueResult(intent_id, job_id, outbox_id, True)


def update_side_effect_intent(
    db: Session,
    *,
    intent_id: str,
    status: str,
    result_code: str | None = None,
    result: dict[str, Any] | None = None,
) -> None:
    """Persist bounded handler evidence without raw provider output."""

    intent = db.get(SideEffectIntent, intent_id)
    if intent is None:
        raise LookupError(f"side-effect intent {intent_id!r} does not exist")
    intent.status = status
    intent.result_code = result_code
    intent.result_json = json.dumps(result, sort_keys=True, separators=(",", ":")) if result else None
    intent.updated_at = utcnow()
    if status in {"succeeded", "dry_run", "dead_lettered", "cancelled", "ambiguous"}:
        intent.completed_at = intent.updated_at
    db.flush()
