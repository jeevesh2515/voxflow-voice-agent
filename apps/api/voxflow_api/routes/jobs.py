"""Tenant-safe operational visibility for Day 28 durable jobs and outbox events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import JobOutbox, JobRun, get_session
from ..jobs.staging import campaign_activation_mode, canary_tenant_ids, durable_campaign_dry_run

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@router.get("/health")
def get_job_health(
    tenant_id: str = Query("varun", min_length=1),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Return tenant-scoped queue, lease, and outbox health without job payloads."""

    now = datetime.now(timezone.utc)
    status_rows = (
        db.query(JobRun.status, func.count(JobRun.id))
        .filter(JobRun.tenant_id == tenant_id)
        .group_by(JobRun.status)
        .all()
    )
    status_counts = {status: count for status, count in status_rows}
    for status in ("ready", "running", "retry_scheduled", "succeeded", "dead_lettered", "cancelled"):
        status_counts.setdefault(status, 0)

    oldest_ready = (
        db.query(JobRun.scheduled_at)
        .filter(
            JobRun.tenant_id == tenant_id,
            JobRun.status.in_(("ready", "retry_scheduled")),
        )
        .order_by(JobRun.scheduled_at.asc())
        .first()
    )
    active_leases = (
        db.query(JobRun)
        .filter(
            JobRun.tenant_id == tenant_id,
            JobRun.status == "running",
            JobRun.lease_expires_at.is_not(None),
            JobRun.lease_expires_at > now,
        )
        .count()
    )
    expired_leases = (
        db.query(JobRun)
        .filter(
            JobRun.tenant_id == tenant_id,
            JobRun.status == "running",
            JobRun.lease_expires_at.is_not(None),
            JobRun.lease_expires_at <= now,
        )
        .count()
    )
    unpublished = (
        db.query(JobOutbox)
        .filter(JobOutbox.tenant_id == tenant_id, JobOutbox.published_at.is_(None))
        .count()
    )
    oldest_outbox = (
        db.query(JobOutbox.created_at)
        .filter(JobOutbox.tenant_id == tenant_id, JobOutbox.published_at.is_(None))
        .order_by(JobOutbox.created_at.asc())
        .first()
    )

    return {
        "tenant_id": tenant_id,
        "activation_mode": campaign_activation_mode(),
        "rollout": {
            "canary_allowed": tenant_id in canary_tenant_ids(),
            "dry_run": durable_campaign_dry_run(),
        },
        "status_counts": status_counts,
        "active_leases": active_leases,
        "expired_leases": expired_leases,
        "oldest_ready_at": _iso(oldest_ready[0]) if oldest_ready else None,
        "outbox": {
            "unpublished": unpublished,
            "oldest_unpublished_at": _iso(oldest_outbox[0]) if oldest_outbox else None,
        },
    }


@router.get("")
def list_recent_jobs(
    tenant_id: str = Query("varun", min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """List safe job metadata for operators; raw payloads are deliberately omitted."""

    jobs = (
        db.query(JobRun)
        .filter(JobRun.tenant_id == tenant_id)
        .order_by(JobRun.updated_at.desc(), JobRun.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "attempt": job.attempt,
            "max_attempts": job.max_attempts,
            "priority": job.priority,
            "next_run_at": _iso(job.next_run_at),
            "lease_owner": job.lease_owner,
            "lease_expires_at": _iso(job.lease_expires_at),
            "last_error_code": job.last_error_code,
            "created_at": _iso(job.created_at),
            "updated_at": _iso(job.updated_at),
        }
        for job in jobs
    ]
