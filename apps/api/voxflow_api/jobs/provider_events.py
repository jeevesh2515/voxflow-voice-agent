"""Day 32 provider callback lifecycle reconciliation primitives."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.orm import Session

from ..db import (
    CampaignQueue,
    JobAttempt,
    JobRun,
    ProviderCallbackQuarantine,
    ProviderEvent,
    ProviderOperation,
)
from .reconciliation import reconcile_campaign_provider_operation


ProviderEventType = Literal[
    "request_accepted",
    "connected",
    "ended",
    "recording_ready",
    "business_outcome",
]

TERMINAL_OPERATION_STATUSES = {"confirmed", "failed_permanent", "dry_run"}
TERMINAL_JOB_STATUSES = {"succeeded", "cancelled", "dead_lettered"}
SUCCESS_OUTCOMES = {"completed", "confirmed", "resolved", "success", "successful"}
FAILURE_OUTCOMES = {"failed", "failed_permanent", "busy", "no_answer", "cancelled", "rejected"}


@dataclass(frozen=True)
class CallbackApplyResult:
    state: str
    provider_event_id: str
    operation_id: str | None
    tenant_id: str | None
    apply_status: str
    anomaly_code: str | None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalise_outcome(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_")


def _operation_status(event_type: ProviderEventType, outcome: str | None) -> str | None:
    if event_type in {"request_accepted", "connected"}:
        return "accepted"
    if event_type in {"ended", "business_outcome"}:
        normalized = _normalise_outcome(outcome)
        if normalized in SUCCESS_OUTCOMES:
            return "confirmed"
        if normalized in FAILURE_OUTCOMES:
            return "failed_permanent"
    return None


def _latest_event(db: Session, operation_id: str) -> ProviderEvent | None:
    return (
        db.query(ProviderEvent)
        .filter(ProviderEvent.provider_operation_id == operation_id)
        .order_by(ProviderEvent.occurred_at.desc(), ProviderEvent.id.desc())
        .first()
    )


def _job_for_operation(db: Session, operation: ProviderOperation) -> JobRun | None:
    return (
        db.query(JobRun)
        .filter(
            JobRun.tenant_id == operation.tenant_id,
            JobRun.idempotency_key == operation.idempotency_key,
        )
        .one_or_none()
    )


def _finish_job_from_callback(
    db: Session,
    *,
    operation: ProviderOperation,
    provider_status: str,
    now: datetime,
) -> None:
    """Finalize a callback-owned durable job exactly once.

    Callback authority is restricted to a previously stored ProviderOperation
    selected by provider/call ID after signature validation. This guarded
    transition deliberately does not require a live worker lease: the original
    worker may be in retry_scheduled while the provider emits the authoritative
    terminal observation.
    """

    job = _job_for_operation(db, operation)
    if job is None or job.status in TERMINAL_JOB_STATUSES:
        return

    job.status = "succeeded" if provider_status == "confirmed" else "dead_lettered"
    job.finished_at = now
    job.lease_owner = None
    job.lease_expires_at = None
    if provider_status == "failed_permanent":
        job.last_error_code = "provider_callback_failed_permanent"
        job.last_error_json = json.dumps({"source": "provider_callback"}, sort_keys=True)
    else:
        job.last_error_code = None
        job.last_error_json = None

    attempt = (
        db.query(JobAttempt)
        .filter(JobAttempt.job_id == job.id)
        .order_by(JobAttempt.attempt_no.desc(), JobAttempt.id.desc())
        .first()
    )
    if attempt is not None and attempt.outcome == "running":
        attempt.outcome = "succeeded" if provider_status == "confirmed" else "failed_permanent"
        attempt.finished_at = now
        if provider_status == "failed_permanent":
            attempt.error_code = "provider_callback_failed_permanent"
            attempt.error_json = json.dumps({"source": "provider_callback"}, sort_keys=True)


def _mark_connected_queue(db: Session, operation: ProviderOperation, provider_call_id: str) -> None:
    job = _job_for_operation(db, operation)
    if job is None:
        return
    try:
        queue_id = str(json.loads(job.payload_json or "{}").get("campaign_queue_id", ""))
    except json.JSONDecodeError:
        return
    if not queue_id:
        return
    item = (
        db.query(CampaignQueue)
        .filter(CampaignQueue.id == queue_id, CampaignQueue.tenant_id == operation.tenant_id)
        .one_or_none()
    )
    if item is not None and item.status not in {"completed", "failed", "cancelled"}:
        item.status = "answered"
        item.call_id = provider_call_id or item.call_id


def quarantine_callback(
    db: Session,
    *,
    provider: str,
    provider_event_id: str,
    provider_call_id: str,
    event_type: str,
    payload_hash: str,
    now: datetime,
    reason_code: str = "unknown_provider_operation",
) -> CallbackApplyResult:
    """Persist one trusted, unmatched observation with no tenant mutation."""

    existing = (
        db.query(ProviderCallbackQuarantine)
        .filter(
            ProviderCallbackQuarantine.provider == provider,
            ProviderCallbackQuarantine.provider_event_id == provider_event_id,
        )
        .one_or_none()
    )
    if existing is not None:
        return CallbackApplyResult("duplicate", provider_event_id, None, None, "duplicate", existing.reason_code)

    db.add(
        ProviderCallbackQuarantine(
            id=f"pcq-{uuid.uuid4().hex[:20]}",
            provider=provider,
            provider_event_id=provider_event_id,
            provider_call_id=provider_call_id,
            event_type=event_type,
            payload_hash=payload_hash,
            reason_code=reason_code,
            received_at=now,
            created_at=now,
        )
    )
    db.flush()
    return CallbackApplyResult(
        "quarantined",
        provider_event_id,
        None,
        None,
        "quarantined",
        reason_code,
    )


def apply_provider_callback(
    db: Session,
    *,
    provider: str,
    provider_event_id: str,
    provider_call_id: str,
    event_type: ProviderEventType,
    occurred_at: datetime,
    outcome: str | None,
    payload_hash: str,
    now: datetime | None = None,
) -> CallbackApplyResult:
    """Deduplicate and reconcile one already authenticated provider callback.

    The provider operation is located only by the stored provider/call ID. Tenant
    information is never accepted as callback input. Event records remain
    immutable even when they are late or out of order.
    """

    applied_at = _as_utc(now or datetime.now(timezone.utc))
    occurred_at = _as_utc(occurred_at)
    existing = (
        db.query(ProviderEvent)
        .filter(
            ProviderEvent.provider == provider,
            ProviderEvent.provider_event_id == provider_event_id,
        )
        .one_or_none()
    )
    if existing is not None:
        return CallbackApplyResult(
            "duplicate",
            provider_event_id,
            existing.provider_operation_id,
            existing.tenant_id,
            "duplicate",
            existing.anomaly_code,
        )

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
        return quarantine_callback(
            db,
            provider=provider,
            provider_event_id=provider_event_id,
            provider_call_id=provider_call_id,
            event_type=event_type,
            payload_hash=payload_hash,
            now=applied_at,
            reason_code=(
                "ambiguous_provider_operation"
                if len(operations) > 1
                else "unsupported_provider_operation"
                if operations
                else "unknown_provider_operation"
            ),
        )
    operation = operations[0]

    desired_status = _operation_status(event_type, outcome)
    latest = _latest_event(db, operation.id)
    apply_status = "applied"
    anomaly_code: str | None = None
    should_reconcile = desired_status is not None

    if operation.status in TERMINAL_OPERATION_STATUSES:
        should_reconcile = False
        apply_status = "ignored_terminal"
        anomaly_code = "terminal_operation"
    elif latest is not None and occurred_at < _as_utc(latest.occurred_at):
        # A terminal observation is still allowed to finish an operation; a late
        # non-terminal callback only adds history and cannot regress queue state.
        if desired_status not in {"confirmed", "failed_permanent"}:
            should_reconcile = False
            apply_status = "ignored_out_of_order"
            anomaly_code = "out_of_order_event"
        else:
            anomaly_code = "terminal_before_prior_event"
    elif event_type in {"ended", "business_outcome"} and desired_status is None:
        should_reconcile = False
        apply_status = "recorded_unresolved_outcome"
        anomaly_code = "unrecognised_terminal_outcome"

    event = ProviderEvent(
        id=f"pev-{uuid.uuid4().hex[:20]}",
        tenant_id=operation.tenant_id,
        provider_operation_id=operation.id,
        provider=provider,
        provider_event_id=provider_event_id,
        provider_call_id=provider_call_id,
        event_type=event_type,
        occurred_at=occurred_at,
        payload_hash=payload_hash,
        normalized_payload_json=json.dumps(
            {"outcome": _normalise_outcome(outcome) or None},
            sort_keys=True,
        ),
        apply_status=apply_status,
        anomaly_code=anomaly_code,
        applied_at=applied_at,
        created_at=applied_at,
    )
    db.add(event)
    db.flush()

    if should_reconcile and desired_status is not None:
        reconcile_campaign_provider_operation(
            db,
            operation_id=operation.id,
            provider_status=desired_status,
            provider_id=provider_call_id,
            now=applied_at,
        )
        if event_type == "connected":
            _mark_connected_queue(db, operation, provider_call_id)
        if desired_status in {"confirmed", "failed_permanent"}:
            _finish_job_from_callback(
                db,
                operation=operation,
                provider_status=desired_status,
                now=applied_at,
            )
        db.flush()

    return CallbackApplyResult(
        "applied" if apply_status == "applied" else "recorded",
        provider_event_id,
        operation.id,
        operation.tenant_id,
        apply_status,
        anomaly_code,
    )
