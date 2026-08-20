"""Controlled Day 29 handler for ``campaign.target.dispatch`` durable jobs."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ..db import CampaignQueue, OutboundCampaign, SessionLocal
from ..integrations.dial import DialClient
from ..tasks.campaign_worker import build_campaign_instruction, is_within_calling_window
from .provider_operations import reserve_provider_operation, update_provider_operation
from .retry import PermanentJobError, RetryableJobError
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


class CampaignDispatchHandler:
    """Execute one canary campaign target with durable provider reconciliation.

    The handler never creates a second external request for an operation that is
    already ``requested`` with unknown acceptance or ``accepted`` with a provider
    call id. A retry therefore reconciles durable state instead of blind redial.
    """

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] = SessionLocal,
        provider_call: ProviderCall = _default_provider_call,
        dry_run: Callable[[], bool] = durable_campaign_dry_run,
    ) -> None:
        self.session_factory = session_factory
        self.provider_call = provider_call
        self.dry_run = dry_run

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
            if item.status in {"completed", "dialing", "answered"}:
                # A prior accepted provider operation already owns the side effect.
                return
            if campaign.status not in {"active", "running"}:
                raise RetryableJobError("campaign_not_active", "campaign must be explicitly staged active", 300)
            if not item.recipient_phone.startswith("+"):
                raise PermanentJobError("invalid_recipient_phone", "recipient must use E.164 format")
            if not is_within_calling_window():
                raise RetryableJobError("outside_calling_window", "campaign call window is closed", 900)

            try:
                metadata = json.loads(item.context_data_json or "{}")
            except json.JSONDecodeError as exc:
                raise PermanentJobError("invalid_campaign_context", str(exc)) from exc
            if not isinstance(metadata, dict):
                raise PermanentJobError("invalid_campaign_context", "campaign context must be a JSON object")

            instruction = build_campaign_instruction(
                campaign.campaign_type,
                item.recipient_name,
                metadata,
            )
            request_hash = hashlib.sha256(
                f"{item.recipient_phone}\n{instruction}".encode("utf-8")
            ).hexdigest()
            operation = reserve_provider_operation(
                db,
                tenant_id=context.tenant_id,
                provider="dial",
                operation_type="outbound_call",
                idempotency_key=context.idempotency_key,
                request_hash=request_hash,
            )
            db.commit()

            # Do not redial ambiguous or previously accepted work. A future
            # callback/poll reconciler can confirm provider state from its id.
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
                raise PermanentJobError("provider_operation_failed_permanent", "provider rejected the original request")

            if self.dry_run():
                item.status = "completed"
                item.attempts_made += 1
                item.call_id = f"dry-{context.idempotency_key[-12:]}"
                item.transcript_summary = "Day 29 canary dry run: provider request intentionally not sent."
                campaign.successful_calls += 1
                update_provider_operation(db, operation_id=operation.id, status="dry_run", provider_id=item.call_id)
                db.commit()
                return

            if not context.renew_lease():
                raise RetryableJobError("lease_not_renewed", "worker lost ownership before provider request", 5)

            result = self.provider_call(item.recipient_phone, instruction)
            if result.get("ok"):
                provider_id = str(result.get("call", {}).get("id", "")) or None
                if provider_id is None:
                    raise RetryableJobError("provider_missing_call_id", "provider accepted request without a call identifier", 60)
                item.status = "dialing"
                item.attempts_made += 1
                item.call_id = provider_id
                item.transcript_summary = "Day 29 canary dispatch accepted by provider; awaiting callback reconciliation."
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
