"""Day 27 tests for durable worker execution, retries, and graceful draining."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from voxflow_api.db import JobAttempt, JobRun, SessionLocal, reset_db
from voxflow_api.jobs.enqueue import enqueue_campaign_target
from voxflow_api.jobs.repository import DEAD_LETTERED, RETRY_SCHEDULED, SUCCEEDED
from voxflow_api.jobs.retry import PermanentJobError, RetryableJobError, full_jitter_delay, retry_decision
from voxflow_api.jobs.worker import WorkerRuntime
from voxflow_api.seed import seed


@pytest.fixture(autouse=True)
def fresh_database():
    reset_db()
    seed(reset=True)


def _now() -> datetime:
    return datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def _enqueue(queue_id: str, *, max_attempts: int = 3) -> str:
    db = SessionLocal()
    try:
        result = enqueue_campaign_target(
            db,
            tenant_id="varun",
            campaign_id="cmp-day27",
            campaign_queue_id=queue_id,
            max_attempts=max_attempts,
        )
        db.commit()
        return result.job_id
    finally:
        db.close()


def _job(job_id: str) -> JobRun:
    db = SessionLocal()
    try:
        return db.get(JobRun, job_id)
    finally:
        db.close()


def _attempt(job_id: str) -> JobAttempt:
    db = SessionLocal()
    try:
        return db.query(JobAttempt).filter(JobAttempt.job_id == job_id).one()
    finally:
        db.close()


def test_full_jitter_and_provider_retry_delay_are_deterministic_when_injected():
    assert full_jitter_delay(1, base_seconds=10, max_seconds=900, random_value=lambda: 0.5) == 5
    assert full_jitter_delay(5, base_seconds=10, max_seconds=90, random_value=lambda: 1.0) == 90
    decision = retry_decision(1, retry_after_seconds=17, max_seconds=90)
    assert decision.delay_seconds == 17
    assert decision.source == "provider"


def test_worker_completes_registered_handler_and_records_success():
    job_id = _enqueue("cq-day27-success")
    handled: list[str] = []
    runtime = WorkerRuntime(
        session_factory=SessionLocal,
        handlers={"campaign.target.dispatch": lambda context: handled.append(context.job_id)},
        worker_id="worker-success",
        now=_now,
    )

    result = runtime.run_once()

    assert result.claimed == 1
    assert result.succeeded == 1
    assert handled == [job_id]
    assert _job(job_id).status == SUCCEEDED
    assert _attempt(job_id).outcome == SUCCEEDED


def test_worker_schedules_retry_with_full_jitter_and_error_evidence():
    job_id = _enqueue("cq-day27-retry")

    def transient_failure(_context):
        raise RetryableJobError("provider_timeout", "gateway timed out")

    runtime = WorkerRuntime(
        session_factory=SessionLocal,
        handlers={"campaign.target.dispatch": transient_failure},
        worker_id="worker-retry",
        now=_now,
        base_retry_seconds=10,
        random_value=lambda: 0.5,
    )

    result = runtime.run_once()

    job = _job(job_id)
    attempt = _attempt(job_id)
    assert result.claimed == 1
    assert result.retried == 1
    assert job.status == RETRY_SCHEDULED
    assert _as_utc(job.next_run_at) == _now() + timedelta(seconds=5)
    assert job.last_error_code == "provider_timeout"
    assert attempt.outcome == RETRY_SCHEDULED
    assert attempt.error_code == "provider_timeout"


def test_worker_dead_letters_permanent_failure_and_unregistered_handler():
    permanent_id = _enqueue("cq-day27-permanent")
    missing_id = _enqueue("cq-day27-unregistered")

    def policy_failure(_context):
        raise PermanentJobError("opted_out", "recipient withdrew consent")

    runtime = WorkerRuntime(
        session_factory=SessionLocal,
        handlers={"campaign.target.dispatch": policy_failure},
        worker_id="worker-dead-letter",
        now=_now,
        batch_size=2,
    )

    # Make one row intentionally unhandled while retaining its durable job.
    db = SessionLocal()
    try:
        db.get(JobRun, missing_id).job_type = "unknown.handler"
        db.commit()
    finally:
        db.close()

    result = runtime.run_once()

    assert result.claimed == 2
    assert result.dead_lettered == 2
    assert _job(permanent_id).status == DEAD_LETTERED
    assert _job(permanent_id).last_error_code == "opted_out"
    assert _job(missing_id).status == DEAD_LETTERED
    assert _job(missing_id).last_error_code == "unregistered_handler"


def test_exhausted_retryable_error_becomes_dead_lettered_without_a_future_claim():
    job_id = _enqueue("cq-day27-exhausted", max_attempts=1)

    def transient_failure(_context):
        raise RetryableJobError("provider_429", "rate limited")

    runtime = WorkerRuntime(
        session_factory=SessionLocal,
        handlers={"campaign.target.dispatch": transient_failure},
        worker_id="worker-exhausted",
        now=_now,
        random_value=lambda: 0.1,
    )

    result = runtime.run_once()

    job = _job(job_id)
    assert result.dead_lettered == 1
    assert result.retried == 0
    assert job.status == DEAD_LETTERED
    assert job.last_error_code == "provider_429"


def test_graceful_drain_stops_new_claims_after_the_current_batch_finishes():
    first_id = _enqueue("cq-day27-drain-first")
    second_id = _enqueue("cq-day27-drain-second")
    handled: list[str] = []
    runtime: WorkerRuntime

    def drain_after_first(context):
        handled.append(context.job_id)
        runtime.request_drain()

    runtime = WorkerRuntime(
        session_factory=SessionLocal,
        handlers={"campaign.target.dispatch": drain_after_first},
        worker_id="worker-drain",
        now=_now,
        batch_size=1,
    )

    first = runtime.run_once()
    second = runtime.run_once()

    assert first.succeeded == 1
    assert runtime.draining is True
    assert second.claimed == 0
    assert handled == [first_id]
    assert _job(first_id).status == SUCCEEDED
    assert _job(second_id).status == "ready"
