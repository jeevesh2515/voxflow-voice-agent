"""Day 26 tests for atomic job claiming, leases, and stale-worker protection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from voxflow_api.db import JobAttempt, JobRun, SessionLocal, reset_db
from voxflow_api.jobs.enqueue import enqueue_campaign_target
from voxflow_api.jobs.repository import (
    DEAD_LETTERED,
    RUNNING,
    SUCCEEDED,
    claim_jobs,
    complete_job,
    extend_lease,
    recover_expired_leases,
)
from voxflow_api.seed import seed


@pytest.fixture(autouse=True)
def fresh_database():
    reset_db()
    seed(reset=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes even for timezone-aware SQLAlchemy fields."""

    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def _enqueue_target(queue_id: str, *, priority: int = 0, max_attempts: int = 3) -> str:
    db = SessionLocal()
    try:
        result = enqueue_campaign_target(
            db,
            tenant_id="varun",
            campaign_id="cmp-day26",
            campaign_queue_id=queue_id,
            priority=priority,
            max_attempts=max_attempts,
        )
        db.commit()
        return result.job_id
    finally:
        db.close()


def _get_job(job_id: str) -> JobRun:
    db = SessionLocal()
    try:
        return db.get(JobRun, job_id)
    finally:
        db.close()


def test_claim_is_exclusive_and_creates_an_attempt_record():
    job_id = _enqueue_target("cq-day26-claim")
    now = _now()

    first = SessionLocal()
    try:
        claimed_by_a = claim_jobs(first, worker_id="worker-a", batch_size=1, now=now)
        first.commit()
    finally:
        first.close()

    second = SessionLocal()
    try:
        claimed_by_b = claim_jobs(second, worker_id="worker-b", batch_size=1, now=now)
        second.commit()
    finally:
        second.close()

    assert [job.id for job in claimed_by_a] == [job_id]
    assert claimed_by_b == []

    db = SessionLocal()
    try:
        job = db.get(JobRun, job_id)
        attempts = db.query(JobAttempt).filter(JobAttempt.job_id == job_id).all()
        assert job.status == RUNNING
        assert job.lease_owner == "worker-a"
        assert job.attempt == 1
        assert _as_utc(job.lease_expires_at) == now + timedelta(seconds=90)
        assert len(attempts) == 1
        assert attempts[0].worker_id == "worker-a"
        assert attempts[0].outcome == RUNNING
    finally:
        db.close()


def test_highest_priority_due_job_is_claimed_first_and_type_filters_apply():
    low_id = _enqueue_target("cq-day26-low", priority=1)
    high_id = _enqueue_target("cq-day26-high", priority=10)
    other_id = _enqueue_target("cq-day26-other", priority=99)

    db = SessionLocal()
    try:
        other = db.get(JobRun, other_id)
        other.job_type = "notification.send"
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        claimed = claim_jobs(
            db,
            worker_id="worker-priority",
            batch_size=2,
            job_types=["campaign.target.dispatch"],
            now=_now(),
        )
        db.commit()
    finally:
        db.close()

    assert [job.id for job in claimed] == [high_id, low_id]


def test_lease_can_be_extended_and_owner_can_complete_before_extended_expiry():
    job_id = _enqueue_target("cq-day26-extend")
    now = _now()

    db = SessionLocal()
    try:
        claim_jobs(db, worker_id="worker-a", batch_size=1, lease_seconds=10, now=now)
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        assert extend_lease(
            db,
            job_id=job_id,
            worker_id="worker-a",
            lease_seconds=30,
            now=now + timedelta(seconds=5),
        ) is True
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        assert complete_job(
            db,
            job_id=job_id,
            worker_id="worker-a",
            now=now + timedelta(seconds=20),
        ) is True
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        job = db.get(JobRun, job_id)
        attempt = db.query(JobAttempt).filter(JobAttempt.job_id == job_id).one()
        assert job.status == SUCCEEDED
        assert job.lease_owner is None
        assert job.lease_expires_at is None
        assert attempt.outcome == SUCCEEDED
        assert _as_utc(attempt.finished_at) == now + timedelta(seconds=20)
    finally:
        db.close()


def test_stale_worker_cannot_complete_after_lease_recovery_and_reclaim():
    job_id = _enqueue_target("cq-day26-stale")
    now = _now()

    db = SessionLocal()
    try:
        claim_jobs(db, worker_id="worker-a", batch_size=1, lease_seconds=10, now=now)
        db.commit()
    finally:
        db.close()

    recovery_time = now + timedelta(seconds=11)
    db = SessionLocal()
    try:
        recovery = recover_expired_leases(db, now=recovery_time)
        db.commit()
    finally:
        db.close()

    assert recovery.retried == 1
    assert recovery.dead_lettered == 0

    db = SessionLocal()
    try:
        assert complete_job(
            db,
            job_id=job_id,
            worker_id="worker-a",
            now=recovery_time,
        ) is False
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        claimed_by_b = claim_jobs(
            db,
            worker_id="worker-b",
            batch_size=1,
            lease_seconds=30,
            now=recovery_time,
        )
        db.commit()
    finally:
        db.close()

    assert [job.id for job in claimed_by_b] == [job_id]

    db = SessionLocal()
    try:
        assert complete_job(
            db,
            job_id=job_id,
            worker_id="worker-b",
            now=recovery_time + timedelta(seconds=1),
        ) is True
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        job = db.get(JobRun, job_id)
        attempts = (
            db.query(JobAttempt)
            .filter(JobAttempt.job_id == job_id)
            .order_by(JobAttempt.attempt_no)
            .all()
        )
        assert job.status == SUCCEEDED
        assert job.attempt == 2
        assert [attempt.outcome for attempt in attempts] == ["lease_expired", SUCCEEDED]
    finally:
        db.close()


def test_expired_job_with_no_attempts_remaining_is_dead_lettered():
    job_id = _enqueue_target("cq-day26-dead", max_attempts=1)
    now = _now()

    db = SessionLocal()
    try:
        claim_jobs(db, worker_id="worker-a", batch_size=1, lease_seconds=10, now=now)
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        recovery = recover_expired_leases(db, now=now + timedelta(seconds=11))
        db.commit()
    finally:
        db.close()

    assert recovery.retried == 0
    assert recovery.dead_lettered == 1

    db = SessionLocal()
    try:
        job = db.get(JobRun, job_id)
        assert job.status == DEAD_LETTERED
        assert _as_utc(job.finished_at) == now + timedelta(seconds=11)
        assert job.last_error_code == "lease_expired"
    finally:
        db.close()
