"""Day 27 synchronous durable worker runtime.

The runtime intentionally owns no durable state. It claims a bounded batch,
commits those leases, executes handlers outside of database transactions, and
uses conditional repository transitions to record success, retry, or failure.
"""

from __future__ import annotations

import json
import os
import random
import signal
import socket
import time
import uuid
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Event
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ..db import JobRun
from .repository import (
    DEAD_LETTERED,
    RETRY_SCHEDULED,
    SUCCEEDED,
    claim_jobs,
    complete_job,
    dead_letter_job,
    extend_lease,
    schedule_retry,
    utcnow,
)
from .retry import PermanentJobError, RetryableJobError, retry_decision


@dataclass(frozen=True)
class JobContext:
    """Read-only execution context provided to a job handler."""

    job_id: str
    tenant_id: str
    job_type: str
    attempt: int
    trace_id: str | None
    worker_id: str
    payload: dict[str, Any]
    renew_lease: Callable[[], bool]


@dataclass(frozen=True)
class WorkerRunResult:
    """Counters returned by one bounded polling iteration."""

    claimed: int = 0
    succeeded: int = 0
    retried: int = 0
    dead_lettered: int = 0
    stale: int = 0


JobHandler = Callable[[JobContext], None]


def build_worker_id(pool_name: str, *, environment: str | None = None) -> str:
    """Create a process-instance identity safe for lease ownership checks."""

    env = environment or os.getenv("ENVIRONMENT", "local")
    return f"{env}:{pool_name}:{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


class WorkerRuntime:
    """Configurable worker process that safely runs registered durable handlers."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        handlers: Mapping[str, JobHandler],
        pool_name: str = "default",
        worker_id: str | None = None,
        job_types: tuple[str, ...] | None = None,
        batch_size: int = 5,
        max_concurrency: int = 1,
        lease_seconds: int = 90,
        poll_interval_seconds: float = 1.0,
        base_retry_seconds: float = 5.0,
        max_retry_seconds: float = 900.0,
        now: Callable[[], datetime] = utcnow,
        sleep: Callable[[float], None] = time.sleep,
        random_value: Callable[[], float] | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be at least 1")
        if poll_interval_seconds < 0:
            raise ValueError("poll_interval_seconds must be non-negative")

        self.session_factory = session_factory
        self.handlers = dict(handlers)
        self.pool_name = pool_name
        self.worker_id = worker_id or build_worker_id(pool_name)
        self.job_types = job_types
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.lease_seconds = lease_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.base_retry_seconds = base_retry_seconds
        self.max_retry_seconds = max_retry_seconds
        self.now = now
        self.sleep = sleep
        self.random_value = random_value
        self._draining = Event()

    @property
    def draining(self) -> bool:
        return self._draining.is_set()

    def request_drain(self) -> None:
        """Stop future claims while allowing the current bounded batch to finish."""

        self._draining.set()

    def install_signal_handlers(self) -> None:
        """Translate SIGTERM/SIGINT into a safe stop-claiming state.

        This method must be called from the process main thread. In-flight work
        remains lease-protected; once a handler finishes, no additional batch is
        claimed and the runtime exits its loop.
        """

        def _drain(_signum: int, _frame: object) -> None:
            self.request_drain()

        signal.signal(signal.SIGTERM, _drain)
        signal.signal(signal.SIGINT, _drain)

    def _renew_lease(self, job_id: str) -> bool:
        db = self.session_factory()
        try:
            renewed = extend_lease(
                db,
                job_id=job_id,
                worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
                now=self.now(),
            )
            db.commit()
            return renewed
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _context_for(self, job: JobRun) -> JobContext:
        try:
            payload = json.loads(job.payload_json or "{}")
        except json.JSONDecodeError as exc:
            raise PermanentJobError("invalid_payload", str(exc)) from exc
        if not isinstance(payload, dict):
            raise PermanentJobError("invalid_payload", "job payload must be a JSON object")

        return JobContext(
            job_id=job.id,
            tenant_id=job.tenant_id,
            job_type=job.job_type,
            attempt=job.attempt,
            trace_id=job.trace_id,
            worker_id=self.worker_id,
            payload=payload,
            renew_lease=lambda: self._renew_lease(job.id),
        )

    def _transition(self, job: JobRun, outcome: str, *, error_code: str | None = None, error_detail: str = "", retry_after_seconds: float | None = None) -> str:
        """Persist one handler outcome using a fresh transaction boundary."""

        db = self.session_factory()
        at = self.now()
        error_json = json.dumps({"detail": error_detail}, sort_keys=True) if error_detail else None
        try:
            if outcome == SUCCEEDED:
                changed = complete_job(db, job_id=job.id, worker_id=self.worker_id, now=at)
            elif outcome == RETRY_SCHEDULED:
                decision = retry_decision(
                    job.attempt,
                    retry_after_seconds=retry_after_seconds,
                    base_seconds=self.base_retry_seconds,
                    max_seconds=self.max_retry_seconds,
                    random_value=self.random_value or random.random,
                )
                changed = schedule_retry(
                    db,
                    job_id=job.id,
                    worker_id=self.worker_id,
                    next_run_at=at + timedelta(seconds=decision.delay_seconds),
                    error_code=error_code or "retryable_error",
                    error_json=error_json,
                    now=at,
                )
                if not changed:
                    # The job may have reached its attempt cap or lost its lease.
                    changed = dead_letter_job(
                        db,
                        job_id=job.id,
                        worker_id=self.worker_id,
                        error_code=error_code or "retry_exhausted",
                        error_json=error_json,
                        now=at,
                    )
                    outcome = DEAD_LETTERED if changed else "stale"
            else:
                changed = dead_letter_job(
                    db,
                    job_id=job.id,
                    worker_id=self.worker_id,
                    error_code=error_code or "permanent_error",
                    error_json=error_json,
                    now=at,
                )

            db.commit()
            return outcome if changed else "stale"
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _execute_job(self, job: JobRun) -> str:
        try:
            context = self._context_for(job)
            handler = self.handlers.get(job.job_type)
            if handler is None:
                raise PermanentJobError("unregistered_handler", f"no handler for {job.job_type}")
            handler(context)
            return self._transition(job, SUCCEEDED)
        except RetryableJobError as exc:
            return self._transition(
                job,
                RETRY_SCHEDULED,
                error_code=exc.code,
                error_detail=exc.detail,
                retry_after_seconds=exc.retry_after_seconds,
            )
        except PermanentJobError as exc:
            return self._transition(
                job,
                DEAD_LETTERED,
                error_code=exc.code,
                error_detail=exc.detail,
            )
        except Exception as exc:  # bounded by the existing durable attempt cap
            return self._transition(
                job,
                RETRY_SCHEDULED,
                error_code="unhandled_exception",
                error_detail=str(exc),
            )

    def run_once(self) -> WorkerRunResult:
        """Claim and process one bounded batch, unless graceful drain has begun."""

        if self.draining:
            return WorkerRunResult()

        db = self.session_factory()
        try:
            jobs = claim_jobs(
                db,
                worker_id=self.worker_id,
                batch_size=self.batch_size,
                lease_seconds=self.lease_seconds,
                job_types=self.job_types,
                now=self.now(),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        if not jobs:
            return WorkerRunResult()

        if self.max_concurrency == 1:
            outcomes = [self._execute_job(job) for job in jobs]
        else:
            with ThreadPoolExecutor(max_workers=self.max_concurrency, thread_name_prefix=self.pool_name) as executor:
                outcomes = list(executor.map(self._execute_job, jobs))

        return WorkerRunResult(
            claimed=len(jobs),
            succeeded=outcomes.count(SUCCEEDED),
            retried=outcomes.count(RETRY_SCHEDULED),
            dead_lettered=outcomes.count(DEAD_LETTERED),
            stale=outcomes.count("stale"),
        )

    def run_forever(self) -> None:
        """Poll until a graceful drain request stops future claim iterations."""

        while not self.draining:
            result = self.run_once()
            if result.claimed == 0 and not self.draining:
                self.sleep(self.poll_interval_seconds)
