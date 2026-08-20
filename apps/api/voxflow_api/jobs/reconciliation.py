"""Provider outcome reconciliation for Day 29 campaign dispatch operations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from ..db import CampaignQueue, JobRun, OutboundCampaign, ProviderOperation
from .provider_operations import update_provider_operation


@dataclass(frozen=True)
class ReconciliationResult:
    operation_id: str
    job_id: str | None
    queue_id: str | None
    status: str


def reconcile_campaign_provider_operation(
    db: Session,
    *,
    operation_id: str,
    provider_status: str,
    provider_id: str | None = None,
    now: datetime | None = None,
) -> ReconciliationResult:
    """Apply a provider terminal result exactly once to its campaign target.

    The provider operation and its durable job share an idempotency key. This
    lets callbacks/reconciliation find the target without trusting provider
    supplied tenant or queue identifiers.
    """

    operation = db.get(ProviderOperation, operation_id)
    if operation is None:
        raise LookupError(f"provider operation {operation_id!r} does not exist")
    if operation.operation_type != "outbound_call":
        raise ValueError("provider operation is not an outbound call")

    if provider_status not in {"confirmed", "failed_permanent", "accepted"}:
        raise ValueError("unsupported provider reconciliation status")

    update_provider_operation(
        db,
        operation_id=operation.id,
        status=provider_status,
        provider_id=provider_id,
        now=now,
    )

    job = (
        db.query(JobRun)
        .filter(
            JobRun.tenant_id == operation.tenant_id,
            JobRun.idempotency_key == operation.idempotency_key,
        )
        .one_or_none()
    )
    if job is None:
        db.flush()
        return ReconciliationResult(operation.id, None, None, provider_status)

    try:
        payload = json.loads(job.payload_json or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("durable job payload is invalid JSON") from exc
    queue_id = str(payload.get("campaign_queue_id", ""))
    item = (
        db.query(CampaignQueue)
        .filter(CampaignQueue.id == queue_id, CampaignQueue.tenant_id == operation.tenant_id)
        .one_or_none()
    )
    if item is None:
        db.flush()
        return ReconciliationResult(operation.id, job.id, None, provider_status)

    campaign = db.get(OutboundCampaign, item.campaign_id)
    if provider_status == "confirmed":
        if item.status != "completed":
            item.status = "completed"
            item.call_id = provider_id or operation.provider_id or item.call_id
            item.transcript_summary = "Provider outcome confirmed by Day 29 reconciliation."
            if campaign is not None:
                campaign.successful_calls += 1
    elif provider_status == "failed_permanent":
        if item.status != "failed":
            item.status = "failed"
            item.transcript_summary = "Provider reported a permanent campaign dispatch failure."
            if campaign is not None:
                campaign.failed_calls += 1
    elif provider_status == "accepted":
        item.status = "dialing"
        item.call_id = provider_id or operation.provider_id or item.call_id

    db.flush()
    return ReconciliationResult(operation.id, job.id, item.id, provider_status)
