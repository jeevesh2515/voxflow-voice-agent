"""Controlled campaign dispatch with Day 30 tenant policy enforcement."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ..db import CampaignQueue, OutboundCampaign, SessionLocal, TenantCampaignPolicy
from ..integrations.dial import DialClient
from ..tasks.campaign_worker import build_campaign_instruction
from .campaign_policy import (
    PolicyDecision,
    evaluate_campaign_policy,
    record_policy_decision,
    release_dispatch_capacity,
    reserve_dispatch_capacity,
    settle_dispatch_capacity,
)
from .provider_operations import reserve_provider_operation, update_provider_operation
from .repository import utcnow
from .retry import (
    PermanentJobError,
    PolicyCancelledJobError,
    PolicyDeferredJobError,
    RetryableJobError,
)
from .staging import durable_campaign_dry_run
from .worker import JobContext

ProviderCall = Callable[[str, str], dict[str, Any]]


def _default_provider_call(to_number: str, instruction: str) -> dict[str, Any]:
    """Synchronously invoke the existing async Dial adapter from a worker thread."""

    return asyncio.run(
        DialClient().place_outbound_call(
            to_number=to_number,
            instruction=instruction,
            language="hi",
        )
    )


def _is_permanent_provider_error(error_code: str) -> bool:
    return error_code.startswith("http_4") and error_code not in {"http_408", "http_429"}


def _policy_detail(result: PolicyDecision) -> str:
    return json.dumps(result.evidence, sort_keys=True)


class CampaignDispatchHandler:
    """Execute one canary target only after tenant policy and capacity approval.

    A policy cancellation is terminal and auditable. A policy deferral records an
    exact next eligibility time without burning the worker's retry budget. An
    existing ambiguous or accepted provider operation always wins over a new dial.
    """

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] = SessionLocal,
        provider_call: ProviderCall = _default_provider_call,
        dry_run: Callable[[], bool] = durable_campaign_dry_run,
        now: Callable[[], datetime] = utcnow,
    ) -> None:
        self.session_factory = session_factory
        self.provider_call = provider_call
        self.dry_run = dry_run
        self.now = now

    def _record_and_raise_policy(
        self,
        db: Session,
        *,
        context: JobContext,
        campaign: OutboundCampaign,
        item: CampaignQueue,
        result: PolicyDecision,
        now: datetime,
    ) -> None:
        record_policy_decision(
            db,
            tenant_id=context.tenant_id,
            job_id=context.job_id,
            campaign_id=campaign.id,
            campaign_queue_id=item.id,
            result=result,
            now=now,
        )
        if result.decision == "cancelled":
            item.status = "cancelled"
            item.transcript_summary = f"Day 30 policy cancellation: {result.reason_code}."
            db.commit()
            raise PolicyCancelledJobError(result.reason_code, _policy_detail(result))
        if result.decision == "deferred":
            if result.next_eligible_at is None:  # defensive contract guard
                raise ValueError("policy defer result requires next_eligible_at")
            item.next_retry_at = result.next_eligible_at
            item.transcript_summary = f"Day 30 policy deferral: {result.reason_code}."
            db.commit()
            raise PolicyDeferredJobError(
                result.reason_code,
                next_eligible_at=result.next_eligible_at,
                detail=_policy_detail(result),
            )

    def __call__(self, context: JobContext) -> None:
        queue_id = str(context.payload.get("campaign_queue_id", ""))
        campaign_id = str(context.payload.get("campaign_id", ""))
        if not queue_id or not campaign_id:
            raise PermanentJobError("invalid_payload", "campaign_id and campaign_queue_id are required")

        db = self.session_factory()
        try:
            item = (
                db.query(CampaignQueue)
                .filter(
                    CampaignQueue.id == queue_id,
                    CampaignQueue.campaign_id == campaign_id,
                    CampaignQueue.tenant_id == context.tenant_id,
                )
                .one_or_none()
            )
            campaign = (
                db.query(OutboundCampaign)
                .filter(
                    OutboundCampaign.id == campaign_id,
                    OutboundCampaign.tenant_id == context.tenant_id,
                )
                .one_or_none()
            )
            if item is None or campaign is None:
                raise PermanentJobError("campaign_target_not_found", "campaign target is not owned by this tenant")
            if item.status in {"completed", "dialing", "answered", "cancelled"}:
                # A terminal policy outcome or a prior provider operation already owns the result.
                return
            if not item.recipient_phone.startswith("+"):
                raise PermanentJobError("invalid_recipient_phone", "recipient must use E.164 format")

            now = self.now()
            policy_result = evaluate_campaign_policy(
                db,
                tenant_id=context.tenant_id,
                campaign=campaign,
                target=item,
                now=now,
            )
            if policy_result.decision != "allowed":
                self._record_and_raise_policy(
                    db,
                    context=context,
                    campaign=campaign,
                    item=item,
                    result=policy_result,
                    now=now,
                )
            record_policy_decision(
                db,
                tenant_id=context.tenant_id,
                job_id=context.job_id,
                campaign_id=campaign.id,
                campaign_queue_id=item.id,
                result=policy_result,
                now=now,
            )

            try:
                metadata = json.loads(item.context_data_json or "{}")
            except json.JSONDecodeError as exc:
                raise PermanentJobError("invalid_campaign_context", str(exc)) from exc
            if not isinstance(metadata, dict):
                raise PermanentJobError("invalid_campaign_context", "campaign context must be a JSON object")
            instruction = build_campaign_instruction(campaign.campaign_type, item.recipient_name, metadata)
            request_hash = hashlib.sha256(f"{item.recipient_phone}\n{instruction}".encode("utf-8")).hexdigest()

            policy = db.get(TenantCampaignPolicy, context.tenant_id)
            if policy is None:  # policy evaluation already guards this; preserve the invariant if changed later.
                raise PermanentJobError("tenant_policy_missing", "tenant campaign policy disappeared during dispatch")
            capacity_result = reserve_dispatch_capacity(
                db,
                tenant_id=context.tenant_id,
                job_id=context.job_id,
                policy=policy,
                now=now,
            )
            if capacity_result.decision != "allowed":
                self._record_and_raise_policy(
                    db,
                    context=context,
                    campaign=campaign,
                    item=item,
                    result=capacity_result,
                    now=now,
                )
            record_policy_decision(
                db,
                tenant_id=context.tenant_id,
                job_id=context.job_id,
                campaign_id=campaign.id,
                campaign_queue_id=item.id,
                result=capacity_result,
                now=now,
            )
            db.commit()

            operation = reserve_provider_operation(
                db,
                tenant_id=context.tenant_id,
                provider="dial",
                operation_type="outbound_call",
                idempotency_key=context.idempotency_key,
                request_hash=request_hash,
            )
            db.commit()

            # Do not redial ambiguous or previously accepted work. A callback or
            # reconciliation pass must resolve the original provider operation.
            if operation.status in {"accepted", "confirmed", "dry_run"}:
                if operation.provider_id and not item.call_id:
                    item.call_id = operation.provider_id
                    item.status = "dialing"
                    db.commit()
                if operation.status == "accepted":
                    raise RetryableJobError(
                        "provider_callback_pending",
                        "provider accepted the call; reconciliation is pending before job completion",
                        60,
                    )
                return
            if operation.status == "requested" and not operation.created:
                raise RetryableJobError(
                    "provider_reconciliation_pending",
                    "provider acceptance is unknown; retry will reconcile rather than redial",
                    60,
                )
            if operation.status == "failed_permanent":
                settle_dispatch_capacity(db, job_id=context.job_id, now=self.now())
                db.commit()
                raise PermanentJobError("provider_operation_failed_permanent", "provider rejected the original request")

            if self.dry_run():
                item.status = "completed"
                item.attempts_made += 1
                item.call_id = f"dry-{context.idempotency_key[-12:]}"
                item.transcript_summary = "Day 30 policy-approved dry run: provider request intentionally not sent."
                campaign.successful_calls += 1
                update_provider_operation(db, operation_id=operation.id, status="dry_run", provider_id=item.call_id)
                settle_dispatch_capacity(db, job_id=context.job_id, now=self.now())
                db.commit()
                return

            if not context.renew_lease():
                release_dispatch_capacity(db, job_id=context.job_id, now=self.now())
                db.commit()
                raise RetryableJobError("lease_not_renewed", "worker lost ownership before provider request", 5)

            result = self.provider_call(item.recipient_phone, instruction)
            if result.get("ok"):
                provider_id = str(result.get("call", {}).get("id", "")) or None
                if provider_id is None:
                    release_dispatch_capacity(db, job_id=context.job_id, now=self.now())
                    db.commit()
                    raise RetryableJobError("provider_missing_call_id", "provider accepted request without a call identifier", 60)
                item.status = "dialing"
                item.attempts_made += 1
                item.call_id = provider_id
                item.transcript_summary = "Day 30 policy-approved dispatch accepted by provider; awaiting reconciliation."
                update_provider_operation(db, operation_id=operation.id, status="accepted", provider_id=provider_id)
                db.commit()
                raise RetryableJobError(
                    "provider_callback_pending",
                    "provider accepted the call; reconciliation is pending before job completion",
                    60,
                )

            error_code = str(result.get("error", "provider_rejected"))
            if _is_permanent_provider_error(error_code):
                update_provider_operation(db, operation_id=operation.id, status="failed_permanent")
                settle_dispatch_capacity(db, job_id=context.job_id, now=self.now())
                db.commit()
                raise PermanentJobError(error_code, str(result.get("detail", "provider rejected request")))
            update_provider_operation(db, operation_id=operation.id, status="failed_retryable")
            db.commit()
            raise RetryableJobError(error_code, str(result.get("detail", "provider request failed")))
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
