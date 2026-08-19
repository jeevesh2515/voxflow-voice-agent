"""Day 25 durable enqueue primitives.

These functions are deliberately synchronous because current dashboard command
routes use the synchronous SQLAlchemy session. They never commit: callers keep
the domain mutation, JobRun, and JobOutbox in one transaction.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import JobOutbox, JobRun


@dataclass(frozen=True)
class EnqueueResult:
    """Result of idempotently recording durable work."""

    job_id: str
    outbox_id: str
    created: bool


def campaign_target_idempotency_key(campaign_queue_id: str) -> str:
    """Return the stable key used across retries for one campaign target."""

    return f"campaign-target:{campaign_queue_id}"


def _existing_enqueue_result(db: Session, *, tenant_id: str, idempotency_key: str) -> EnqueueResult | None:
    job = (
        db.query(JobRun)
        .filter(
            JobRun.tenant_id == tenant_id,
            JobRun.idempotency_key == idempotency_key,
        )
        .one_or_none()
    )
    if job is None:
        return None

    outbox = (
        db.query(JobOutbox)
        .filter(
            JobOutbox.tenant_id == tenant_id,
            JobOutbox.idempotency_key == idempotency_key,
        )
        .one_or_none()
    )
    if outbox is None:
        # A partial pair cannot be manufactured by this implementation because
        # both inserts share a transaction. Treat older/manual data as a fault
        # instead of silently dropping an event.
        raise RuntimeError(f"Durable enqueue {idempotency_key!r} is missing its outbox record")

    return EnqueueResult(job_id=job.id, outbox_id=outbox.id, created=False)


def enqueue_campaign_target(
    db: Session,
    *,
    tenant_id: str,
    campaign_id: str,
    campaign_queue_id: str,
    priority: int = 0,
    max_attempts: int = 6,
    trace_id: str | None = None,
) -> EnqueueResult:
    """Persist a campaign dispatch job and its outbox event atomically.

    The supplied session must be part of the same transaction that creates the
    campaign queue row. Calling this function repeatedly for the same target is
    safe. A uniqueness conflict caused by concurrent HTTP requests rolls back
    only this insert savepoint, then returns the durable pair created by the
    competing request.
    """

    idempotency_key = campaign_target_idempotency_key(campaign_queue_id)
    existing = _existing_enqueue_result(
        db, tenant_id=tenant_id, idempotency_key=idempotency_key,
    )
    if existing:
        return existing

    payload: dict[str, Any] = {
        "campaign_id": campaign_id,
        "campaign_queue_id": campaign_queue_id,
    }
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    job_id = f"job-{uuid.uuid4().hex[:20]}"
    outbox_id = f"out-{uuid.uuid4().hex[:20]}"

    try:
        with db.begin_nested():
            db.add(
                JobRun(
                    id=job_id,
                    tenant_id=tenant_id,
                    job_type="campaign.target.dispatch",
                    payload_json=payload_json,
                    status="ready",
                    priority=priority,
                    idempotency_key=idempotency_key,
                    max_attempts=max_attempts,
                    trace_id=trace_id,
                )
            )
            db.add(
                JobOutbox(
                    id=outbox_id,
                    tenant_id=tenant_id,
                    event_type="campaign.target.queued",
                    aggregate_type="campaign_queue",
                    aggregate_id=campaign_queue_id,
                    payload_json=payload_json,
                    idempotency_key=idempotency_key,
                )
            )
            db.flush()
    except IntegrityError:
        # PostgreSQL and SQLite both keep the outer campaign transaction usable
        # after this savepoint rollback. Reload the winner of the unique-key race.
        db.expire_all()
        existing = _existing_enqueue_result(
            db, tenant_id=tenant_id, idempotency_key=idempotency_key,
        )
        if existing:
            return existing
        raise

    return EnqueueResult(job_id=job_id, outbox_id=outbox_id, created=True)
