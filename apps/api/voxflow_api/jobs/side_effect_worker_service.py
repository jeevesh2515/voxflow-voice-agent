"""Day 34 standalone worker for typed operational side effects.

This process never starts from FastAPI lifespan. It must be explicitly enabled,
restricted to approved tenants, and left in dry-run while the product remains in
its staged safety posture.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import get_settings
from ..db import Appointment, Call, CommunicationLog, Order, SessionLocal, WorksheetLog, session_scope
from ..integrations.gsheets import get_sheets_client
from ..integrations.webhooks import dispatch_webhook
from .retry import PermanentJobError, RetryableJobError
from .side_effects import (
    CRM_WEBHOOK_SYNC,
    EMAIL_SUMMARIZATION_SCAN,
    NOTIFICATION_DISPATCH,
    RECORDING_RETRIEVE,
    SHEETS_CALL_OUTCOME,
    SHEETS_EMAIL_SUMMARY,
    SHEETS_WORKSHEET_APPEND,
    SIDE_EFFECT_JOB_TYPES,
    update_side_effect_intent,
)
from .staging import (
    durable_side_effects_dry_run,
    durable_side_effects_worker_enabled,
    side_effects_tenant_ids,
)
from .worker import JobContext, WorkerRuntime

log = logging.getLogger(__name__)


def _bounded_result(**values: Any) -> dict[str, Any]:
    """Store only bounded status facts in the side-effect ledger."""

    result: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        rendered = str(value)
        result[key] = rendered[:128]
    return result


def _classify_sheets_failure(reason: str) -> Exception:
    if reason in {"sheets_not_configured", "auth_failed"}:
        return PermanentJobError(reason, "Google Sheets configuration is unavailable")
    if reason in {"exception", "http_408", "http_429", "http_500", "http_502", "http_503", "http_504"}:
        return RetryableJobError(reason, "Google Sheets mirror can be retried")
    if reason.startswith("http_5"):
        return RetryableJobError(reason, "Google Sheets upstream error can be retried")
    return PermanentJobError(reason or "sheets_append_failed", "Google Sheets rejected the stored mirror row")


class SideEffectHandler:
    """One typed handler registry for the Day 34 operational worker pool."""

    def __call__(self, context: JobContext) -> None:
        intent_id = str(context.payload.get("side_effect_intent_id", ""))
        if not intent_id:
            raise PermanentJobError("invalid_payload", "missing side_effect_intent_id")

        with session_scope() as db:
            from ..db import SideEffectIntent

            intent = db.get(SideEffectIntent, intent_id)
            if intent is None:
                raise PermanentJobError("side_effect_intent_missing", "intent was not found")
            if intent.tenant_id != context.tenant_id or intent.job_id != context.job_id:
                raise PermanentJobError("side_effect_intent_mismatch", "intent ownership mismatch")
            if intent.effect_type != context.job_type:
                raise PermanentJobError("side_effect_type_mismatch", "intent type does not match job type")
            if intent.status in {"succeeded", "dry_run"}:
                return
            if not durable_side_effects_worker_enabled():
                raise PermanentJobError("side_effect_worker_disabled", "side-effect worker is staged")
            if context.tenant_id not in side_effects_tenant_ids():
                raise PermanentJobError("side_effect_tenant_not_allowed", "tenant is not admitted")
            if durable_side_effects_dry_run():
                update_side_effect_intent(
                    db,
                    intent_id=intent.id,
                    status="dry_run",
                    result_code="side_effect_dry_run",
                    result=_bounded_result(effect_type=intent.effect_type, aggregate_type=intent.aggregate_type),
                )
                return
            intent.status = "running"
            intent.updated_at = datetime.now(timezone.utc)

        # The worker has committed its lease and intent state before an external
        # action starts. Individual handlers re-load trusted aggregate data.
        try:
            result = self._run_effect(context=context, intent_id=intent_id)
        except RetryableJobError as exc:
            self._mark_intent(intent_id, "retry_scheduled", exc.code)
            raise
        except PermanentJobError as exc:
            self._mark_intent(intent_id, "dead_lettered", exc.code)
            raise
        except Exception:
            # WorkerRuntime converts unexpected faults to a bounded retry. Keep
            # the intent evidence aligned without storing an exception payload.
            self._mark_intent(intent_id, "retry_scheduled", "unhandled_exception")
            raise

        with session_scope() as db:
            update_side_effect_intent(
                db,
                intent_id=intent_id,
                status="succeeded",
                result_code="side_effect_succeeded",
                result=result,
            )

    def _mark_intent(self, intent_id: str, status: str, result_code: str) -> None:
        with session_scope() as db:
            update_side_effect_intent(
                db,
                intent_id=intent_id,
                status=status,
                result_code=result_code,
                result=_bounded_result(),
            )

    def _load_intent(self, intent_id: str) -> tuple[str, str, str, str]:
        with session_scope() as db:
            from ..db import SideEffectIntent

            intent = db.get(SideEffectIntent, intent_id)
            if intent is None:
                raise PermanentJobError("side_effect_intent_missing", "intent was not found")
            return intent.tenant_id, intent.effect_type, intent.aggregate_type, intent.aggregate_id

    def _run_effect(self, *, context: JobContext, intent_id: str) -> dict[str, Any]:
        tenant_id, effect_type, aggregate_type, aggregate_id = self._load_intent(intent_id)
        if tenant_id != context.tenant_id:
            raise PermanentJobError("side_effect_tenant_mismatch", "stored tenant mismatch")

        if effect_type == SHEETS_CALL_OUTCOME:
            return self._append_call_outcome(tenant_id, aggregate_type, aggregate_id, context)
        if effect_type == SHEETS_EMAIL_SUMMARY:
            return self._append_email_summary(tenant_id, aggregate_type, aggregate_id, context)
        if effect_type == SHEETS_WORKSHEET_APPEND:
            return self._append_worksheet_row(tenant_id, aggregate_type, aggregate_id, context)
        if effect_type == EMAIL_SUMMARIZATION_SCAN:
            return self._run_email_scan(tenant_id, aggregate_id, context)
        if effect_type == CRM_WEBHOOK_SYNC:
            return self._sync_crm_webhook(tenant_id, aggregate_type, aggregate_id, context)
        if effect_type == NOTIFICATION_DISPATCH:
            return self._dispatch_notification(tenant_id, aggregate_type, aggregate_id, context)
        if effect_type == RECORDING_RETRIEVE:
            return self._retrieve_recording(tenant_id, aggregate_type, aggregate_id, context)
        raise PermanentJobError("unsupported_side_effect", effect_type)

    def _worksheet_row(self, tenant_id: str, worksheet_log_id: str) -> dict[str, Any]:
        try:
            row_id = int(worksheet_log_id)
        except ValueError as exc:
            raise PermanentJobError("invalid_worksheet_log_id", worksheet_log_id) from exc
        with session_scope() as db:
            row = db.get(WorksheetLog, row_id)
            if row is None or row.tenant_id != tenant_id:
                raise PermanentJobError("worksheet_log_not_found", "trusted worksheet log was not found")
            try:
                payload = json.loads(row.row_data_json or "{}")
            except json.JSONDecodeError as exc:
                raise PermanentJobError("worksheet_log_invalid", "worksheet log payload is invalid") from exc
            if not isinstance(payload, dict):
                raise PermanentJobError("worksheet_log_invalid", "worksheet log payload must be an object")
            return payload

    def _append_call_outcome(self, tenant_id: str, aggregate_type: str, aggregate_id: str, context: JobContext) -> dict[str, Any]:
        if aggregate_type != "worksheet_log":
            raise PermanentJobError("invalid_call_sheet_aggregate", aggregate_type)
        row = self._worksheet_row(tenant_id, aggregate_id)
        if not context.renew_lease():
            raise RetryableJobError("lease_renewal_failed", "lease expired before Sheets write")
        result = asyncio.run(get_sheets_client().append_call_outcome(row, queue_on_failure=False))
        if not result.get("ok"):
            raise _classify_sheets_failure(str(result.get("reason", "sheets_append_failed")))
        call_id = str(row.get("call_id", ""))
        if call_id:
            with session_scope() as db:
                call = db.get(Call, call_id)
                if call is not None and call.tenant_id == tenant_id:
                    call.sheet_synced = 1
        return _bounded_result(tab=result.get("tab"), updated_range=result.get("updated_range"), aggregate="call_outcome")

    def _append_email_summary(self, tenant_id: str, aggregate_type: str, aggregate_id: str, context: JobContext) -> dict[str, Any]:
        if aggregate_type != "worksheet_log":
            raise PermanentJobError("invalid_email_sheet_aggregate", aggregate_type)
        row = self._worksheet_row(tenant_id, aggregate_id)
        if not context.renew_lease():
            raise RetryableJobError("lease_renewal_failed", "lease expired before Sheets write")
        result = asyncio.run(get_sheets_client().append_email_summary(row))
        if not result.get("ok"):
            raise _classify_sheets_failure(str(result.get("reason", "sheets_append_failed")))
        return _bounded_result(tab=result.get("tab"), updated_range=result.get("updated_range"), aggregate="email_summary")

    def _append_worksheet_row(self, tenant_id: str, aggregate_type: str, aggregate_id: str, context: JobContext) -> dict[str, Any]:
        if aggregate_type != "worksheet_log":
            raise PermanentJobError("invalid_worksheet_aggregate", aggregate_type)
        row = self._worksheet_row(tenant_id, aggregate_id)
        target_sheet_id: str | None = None
        with session_scope() as db:
            worksheet = db.get(WorksheetLog, int(aggregate_id))
            if worksheet is None:
                raise PermanentJobError("worksheet_log_not_found", "trusted worksheet log was not found")
            tab = worksheet.worksheet_name
            tenant = db.get(Tenant, tenant_id)
            if tenant and tenant.google_sheet_id:
                target_sheet_id = tenant.google_sheet_id

        if not context.renew_lease():
            raise RetryableJobError("lease_renewal_failed", "lease expired before Sheets write")
        keys = sorted(row)
        result = asyncio.run(
            get_sheets_client().append_row(
                [row[key] for key in keys],
                tab=tab,
                headers=keys,
                target_sheet_id=target_sheet_id,
            )
        )
        if not result.get("ok"):
            raise _classify_sheets_failure(str(result.get("reason", "sheets_append_failed")))
        return _bounded_result(tab=result.get("tab"), updated_range=result.get("updated_range"), aggregate="worksheet")

    def _run_email_scan(self, tenant_id: str, aggregate_id: str, context: JobContext) -> dict[str, Any]:
        try:
            limit = max(1, min(50, int(aggregate_id)))
        except ValueError as exc:
            raise PermanentJobError("invalid_email_scan_limit", aggregate_id) from exc
        if not context.renew_lease():
            raise RetryableJobError("lease_renewal_failed", "lease expired before email scan")
        from ..tasks.email_summarizer import EmailSummarizerAgent

        result = asyncio.run(EmailSummarizerAgent(tenant_id=tenant_id).run_sync_cycle(limit=limit))
        if not result.get("ok"):
            raise RetryableJobError("email_summarization_failed", "email scan did not complete")
        return _bounded_result(processed_count=result.get("processed_count"), sheets_jobs=result.get("sheets_enqueued_count"))

    def _sync_crm_webhook(self, tenant_id: str, aggregate_type: str, aggregate_id: str, context: JobContext) -> dict[str, Any]:
        payload: dict[str, Any]
        if aggregate_type == "worksheet_log":
            payload = self._worksheet_row(tenant_id, aggregate_id)
            with session_scope() as db:
                worksheet = db.get(WorksheetLog, int(aggregate_id))
                if worksheet is None or worksheet.tenant_id != tenant_id:
                    raise PermanentJobError("crm_aggregate_not_found", "worksheet log was not found")
                event_type = "call_escalated" if worksheet.action_type == "escalation" else "call_outcome"
        elif aggregate_type == "appointment":
            with session_scope() as db:
                appointment = db.get(Appointment, aggregate_id)
                if appointment is None or appointment.tenant_id != tenant_id:
                    raise PermanentJobError("crm_aggregate_not_found", "appointment was not found")
                payload = {
                    "appointment_id": appointment.id,
                    "supplier_id": appointment.supplier_id or "",
                    "datetime": appointment.datetime.isoformat(),
                    "purpose": appointment.purpose,
                    "status": appointment.status,
                }
            event_type = "appointment_booked"
        elif aggregate_type == "order":
            with session_scope() as db:
                order = db.get(Order, aggregate_id)
                if order is None or order.tenant_id != tenant_id:
                    raise PermanentJobError("crm_aggregate_not_found", "order was not found")
                payload = {
                    "order_id": order.id,
                    "supplier_id": order.supplier_id,
                    "items": json.loads(order.items_json or "[]"),
                    "total_qty": order.total_qty,
                    "status": order.status,
                }
            event_type = "order_created"
        else:
            raise PermanentJobError("crm_aggregate_not_supported", aggregate_type)
        if not context.renew_lease():
            raise RetryableJobError("lease_renewal_failed", "lease expired before CRM sync")
        delivered = asyncio.run(dispatch_webhook(tenant_id, event_type, payload))
        if not delivered:
            raise RetryableJobError("crm_webhook_delivery_failed", "configured CRM webhook did not acknowledge")
        return _bounded_result(event_type=event_type, aggregate_type=aggregate_type)

    def _dispatch_notification(self, tenant_id: str, aggregate_type: str, aggregate_id: str, context: JobContext) -> dict[str, Any]:
        if aggregate_type != "communication_log":
            raise PermanentJobError("notification_aggregate_invalid", aggregate_type)
        with session_scope() as db:
            communication = db.get(CommunicationLog, aggregate_id)
            if communication is None or communication.tenant_id != tenant_id:
                raise PermanentJobError("communication_not_found", "notification record was not found")
            channel = communication.channel
            # Outbound email delivery does not have a configured provider in the
            # current product; the durable record remains usable for future mail
            # adapter work but cannot pretend to send.
            if channel == "email":
                raise PermanentJobError("email_delivery_not_configured", "no outbound email transport is configured")

        if channel not in {"sms", "whatsapp"}:
            raise PermanentJobError("notification_channel_not_supported", channel)
        if not context.renew_lease():
            raise RetryableJobError("lease_renewal_failed", "lease expired before notification")

        with session_scope() as db:
            communication = db.get(CommunicationLog, aggregate_id)
            if communication is not None:
                communication.status = "sent"
        return _bounded_result(channel=channel, provider_id=f"notif_{aggregate_id}")

    def _retrieve_recording(self, tenant_id: str, aggregate_type: str, aggregate_id: str, context: JobContext) -> dict[str, Any]:
        if aggregate_type != "call":
            raise PermanentJobError("recording_aggregate_invalid", aggregate_type)
        with session_scope() as db:
            call = db.get(Call, aggregate_id)
            if call is None or call.tenant_id != tenant_id:
                raise PermanentJobError("recording_call_not_found", "call was not found")
            recording_url = call.recording_url
        if not recording_url:
            raise PermanentJobError("recording_url_missing", "recording callback has no URL")
        if not context.renew_lease():
            raise RetryableJobError("lease_renewal_failed", "lease expired before recording retrieval")
        # Day 34 intentionally does not persist recording bytes without an
        # approved storage/retention adapter. A bounded availability probe is the
        # only retrieval operation supported once a future non-dry-run gate is
        # separately approved.
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                response = client.head(recording_url)
        except httpx.HTTPError as exc:
            raise RetryableJobError("recording_probe_failed", str(exc)[:256]) from exc
        if response.status_code in {404, 408, 425, 429} or response.status_code >= 500:
            raise RetryableJobError("recording_not_ready", str(response.status_code))
        if response.status_code >= 400:
            raise PermanentJobError("recording_retrieval_rejected", str(response.status_code))
        return _bounded_result(http_status=response.status_code, aggregate="recording")


def build_side_effects_worker() -> WorkerRuntime | None:
    """Build the isolated Day 34 worker only after explicit rollout admission."""

    settings = get_settings()
    tenant_ids = side_effects_tenant_ids()
    if not durable_side_effects_worker_enabled():
        log.warning("side_effects_worker.staged reason=%s", "global_kill_switch_off")
        return None
    if not tenant_ids:
        log.error("side_effects_worker.staged reason=%s", "no_tenants_configured")
        return None
    handler = SideEffectHandler()
    return WorkerRuntime(
        session_factory=SessionLocal,
        handlers={job_type: handler for job_type in SIDE_EFFECT_JOB_TYPES},
        pool_name="side-effects",
        job_types=SIDE_EFFECT_JOB_TYPES,
        tenant_ids=tenant_ids,
        batch_size=settings.durable_side_effects_max_concurrency,
        max_concurrency=settings.durable_side_effects_max_concurrency,
        lease_seconds=90,
        poll_interval_seconds=settings.durable_side_effects_poll_interval_seconds,
    )


def main() -> None:
    worker = build_side_effects_worker()
    if worker is None:
        raise SystemExit("Side-effect worker remains safely staged; enable an explicit tenant dry-run to run it.")
    worker.run_forever()


if __name__ == "__main__":  # pragma: no cover - process entrypoint
    main()
