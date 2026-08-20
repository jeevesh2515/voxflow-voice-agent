"""Day 26 durable job claim and lease repository.

A worker must call ``claim_jobs`` in a short transaction, commit the claim, and
only then perform an external side effect. Terminal updates are conditional on
the current lease owner and unexpired lease, so a stale worker cannot overwrite
work recovered and re-leased to another worker.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import update
from sqlalchemy.orm import Session

from ..db import JobAttempt, JobRun

READY = "ready"
RUNNING = "running"
RETRY_SCHEDULED = "retry_scheduled"
SUCCEEDED = "succeeded"
DEAD_LETTERED = "dead_lettered"

CLAIMABLE_STATUSES = (READY, RETRY_SCHEDULED)


@dataclass(frozen=True)
class LeaseRecoveryResult:
    """Count of expired leases made runnable or escalated to dead-letter."""

    retried: int
    dead_lettered: int


def utcnow() -> datetime:
    """Return an injectable UTC clock boundary for deterministic tests."""

    return datetime.now(timezone.utc)


def _claim_query(
    db: Session,
    *,
    now: datetime,
    job_types: Iterable[str] | None,
    tenant_ids: Iterable[str] | None,
):
    query = (
        db.query(JobRun)
        .filter(
            JobRun.status.in_(CLAIMABLE_STATUSES),
            JobRun.scheduled_at <= now,
            JobRun.next_run_at <= now,
            JobRun.attempt < JobRun.max_attempts,
        )
        .order_by(JobRun.priority.desc(), JobRun.scheduled_at.asc(), JobRun.id.asc())
    )
    if job_types:
        query = query.filter(JobRun.job_type.in_(tuple(job_types)))
    if tenant_ids:
        query = query.filter(JobRun.tenant_id.in_(tuple(tenant_ids)))

    # PostgreSQL workers use SKIP LOCKED so concurrently polling workers do not
    # block each other. SQLite lacks row-level locking; tests still verify the
    # state transition contract sequentially.
    if db.get_bind().dialect.name != "sqlite":
        query = query.with_for_update(skip_locked=True)
    return query


def claim_jobs(
    db: Session,
    *,
    worker_id: str,
    batch_size: int,
    lease_seconds: int = 90,
    job_types: Iterable[str] | None = None,
    tenant_ids: Iterable[str] | None = None,
    now: datetime | None = None,
) -> list[JobRun]:
    """Atomically claim a bounded batch of eligible jobs for one worker.

    The caller owns the surrounding transaction. It must commit immediately
    after this function returns and before invoking any external provider. A
    claim creates a corresponding immutable ``JobAttempt`` record.
    """

    if not worker_id.strip():
        raise ValueError("worker_id is required")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if lease_seconds < 1:
        raise ValueError("lease_seconds must be at least 1")

    claimed_at = now or utcnow()
    lease_expires_at = claimed_at + timedelta(seconds=lease_seconds)
    jobs = _claim_query(
        db,
        now=claimed_at,
        job_types=job_types,
        tenant_ids=tenant_ids,
    ).limit(batch_size).all()

    for job in jobs:
        job.status = RUNNING
        job.lease_owner = worker_id
        job.lease_expires_at = lease_expires_at
        job.started_at = job.started_at or claimed_at
        job.attempt += 1
        job.last_error_code = None
        job.last_error_json = None
        db.add(
            JobAttempt(
                id=f"jat-{uuid.uuid4().hex[:20]}",
                job_id=job.id,
                tenant_id=job.tenant_id,
                attempt_no=job.attempt,
                worker_id=worker_id,
                outcome=RUNNING,
                started_at=claimed_at,
            )
        )

    db.flush()
    return jobs


def extend_lease(
    db: Session,
    *,
    job_id: str,
    worker_id: str,
    lease_seconds: int = 90,
    now: datetime | None = None,
) -> bool:
    """Renew an active worker-owned lease without changing its attempt count."""

    if lease_seconds < 1:
        raise ValueError("lease_seconds must be at least 1")
    renewed_at = now or utcnow()
    result = db.execute(
        update(JobRun)
        .where(
            JobRun.id == job_id,
            JobRun.status == RUNNING,
            JobRun.lease_owner == worker_id,
            JobRun.lease_expires_at > renewed_at,
        )
        .values(
            lease_expires_at=renewed_at + timedelta(seconds=lease_seconds),
            updated_at=renewed_at,
        )
    )
    db.flush()
    return result.rowcount == 1


def complete_job(
    db: Session,
    *,
    job_id: str,
    worker_id: str,
    now: datetime | None = None,
) -> bool:
    """Mark a job succeeded only when the caller still owns an active lease.

    A ``False`` return is an expected stale-worker result, not a retry signal.
    The worker must stop and reconcile provider state rather than issue another
    external side effect.
    """

    completed_at = now or utcnow()
    result = db.execute(
        update(JobRun)
        .where(
            JobRun.id == job_id,
            JobRun.status == RUNNING,
            JobRun.lease_owner == worker_id,
            JobRun.lease_expires_at > completed_at,
        )
        .values(
            status=SUCCEEDED,
            lease_owner=None,
            lease_expires_at=None,
            finished_at=completed_at,
            updated_at=completed_at,
        )
    )
    if result.rowcount != 1:
        return False

    db.execute(
        update(JobAttempt)
        .where(
            JobAttempt.job_id == job_id,
            JobAttempt.worker_id == worker_id,
            JobAttempt.outcome == RUNNING,
            JobAttempt.finished_at.is_(None),
        )
        .values(outcome=SUCCEEDED, finished_at=completed_at)
    )
    db.flush()
    return True


def recover_expired_leases(
    db: Session,
    *,
    now: datetime | None = None,
) -> LeaseRecoveryResult:
    """Recover expired running jobs without allowing their old worker to finish.

    Jobs with remaining attempts become immediately claimable again. Exhausted
    jobs are dead-lettered for operator review. Like claims, PostgreSQL uses
    ``SKIP LOCKED`` to let maintenance replicas recover different rows safely.
    """

    recovered_at = now or utcnow()
    query = (
        db.query(JobRun)
        .filter(
            JobRun.status == RUNNING,
            JobRun.lease_expires_at.is_not(None),
            JobRun.lease_expires_at <= recovered_at,
        )
        .order_by(JobRun.lease_expires_at.asc(), JobRun.id.asc())
    )
    if db.get_bind().dialect.name != "sqlite":
        query = query.with_for_update(skip_locked=True)

    retried = 0
    dead_lettered = 0
    for job in query.all():
        db.execute(
            update(JobAttempt)
            .where(
                JobAttempt.job_id == job.id,
                JobAttempt.attempt_no == job.attempt,
                JobAttempt.outcome == RUNNING,
                JobAttempt.finished_at.is_(None),
            )
            .values(outcome="lease_expired", finished_at=recovered_at)
        )
        job.lease_owner = None
        job.lease_expires_at = None
        job.last_error_code = "lease_expired"
        job.last_error_json = '{"reason":"worker_lease_expired"}'

        if job.attempt >= job.max_attempts:
            job.status = DEAD_LETTERED
            job.finished_at = recovered_at
            dead_lettered += 1
        else:
            job.status = RETRY_SCHEDULED
            job.next_run_at = recovered_at
            retried += 1

    db.flush()
    return LeaseRecoveryResult(retried=retried, dead_lettered=dead_lettered)


def schedule_retry(
    db: Session,
    *,
    job_id: str,
    worker_id: str,
    next_run_at: datetime,
    error_code: str,
    error_json: str | None = None,
    now: datetime | None = None,
) -> bool:
    """Release a valid lease and make a transient failure retryable later.

    The retry transition is guarded by the same owner-and-expiry predicates as
    completion. A stale worker cannot postpone or reopen work claimed by a new
    worker.
    """

    scheduled_at = now or utcnow()
    result = db.execute(
        update(JobRun)
        .where(
            JobRun.id == job_id,
            JobRun.status == RUNNING,
            JobRun.lease_owner == worker_id,
            JobRun.lease_expires_at > scheduled_at,
            JobRun.attempt < JobRun.max_attempts,
        )
        .values(
            status=RETRY_SCHEDULED,
            lease_owner=None,
            lease_expires_at=None,
            next_run_at=next_run_at,
            last_error_code=error_code,
            last_error_json=error_json,
            updated_at=scheduled_at,
        )
    )
    if result.rowcount != 1:
        return False

    db.execute(
        update(JobAttempt)
        .where(
            JobAttempt.job_id == job_id,
            JobAttempt.worker_id == worker_id,
            JobAttempt.outcome == RUNNING,
            JobAttempt.finished_at.is_(None),
        )
        .values(outcome=RETRY_SCHEDULED, finished_at=scheduled_at, error_code=error_code, error_json=error_json)
    )
    db.flush()
    return True


def dead_letter_job(
    db: Session,
    *,
    job_id: str,
    worker_id: str,
    error_code: str,
    error_json: str | None = None,
    now: datetime | None = None,
) -> bool:
    """Terminate a valid lease with a human-reviewable terminal failure."""

    failed_at = now or utcnow()
    result = db.execute(
        update(JobRun)
        .where(
            JobRun.id == job_id,
            JobRun.status == RUNNING,
            JobRun.lease_owner == worker_id,
            JobRun.lease_expires_at > failed_at,
        )
        .values(
            status=DEAD_LETTERED,
            lease_owner=None,
            lease_expires_at=None,
            finished_at=failed_at,
            last_error_code=error_code,
            last_error_json=error_json,
            updated_at=failed_at,
        )
    )
    if result.rowcount != 1:
        return False

    db.execute(
        update(JobAttempt)
        .where(
            JobAttempt.job_id == job_id,
            JobAttempt.worker_id == worker_id,
            JobAttempt.outcome == RUNNING,
            JobAttempt.finished_at.is_(None),
        )
        .values(outcome=DEAD_LETTERED, finished_at=failed_at, error_code=error_code, error_json=error_json)
    )
    db.flush()
    return True
