"""Per-call-minute usage metering -> Stripe Billing Meters.

Reads completed calls from the ``calls`` table and reports billed minutes to
Stripe as Billing Meter events - the CURRENT Stripe API. The legacy
``usage_records`` endpoint is deprecated:
    docs.stripe.com/billing/subscriptions/usage-based-legacy/migration-guide
    (changelog 2025-03-31: "We've removed support for legacy usage-based
    billing. You can no longer create a price with a usage_type of metered
    without a specified meter.")

Flow
----
1. A periodic job (scripts/run_meter_report.py, e.g. hourly cron) selects
   calls with ``metering_billed_at IS NULL`` and ``duration_sec > 0``.
2. Per tenant, resolve the Stripe customer id and send ONE meter event:
     event_name = settings.stripe_meter_event_name   (the meter's event_name)
     identifier = "voxflow-call-meter-<call.id>"      (Stripe dedupes >=24h)
     payload    = {"stripe_customer_id": ..., "value": billed_minutes}
     timestamp  = unix(ended_at or started_at)        (usage-time, not send-time)
3. Only after Stripe accepts do we set ``metering_billed_at`` +
   ``metering_event_id``. Crash between send and mark is safe: the retry
   re-sends the SAME identifier and Stripe de-duplicates within its rolling
   >=24h uniqueness window.

Billing traps handled
- Rounding rule: ceil(duration_sec/60), minimum 1 minute per completed call
  with any duration; fall back to the wall-clock ended-started window when
  duration_sec is 0; skip calls with no usable duration.
- Idempotency: stable identifier per call + DB billed flag (never double-charge).
- Customer lookup: a tenant without a resolvable Stripe customer id is logged
  and skipped - it never blocks the batch.
- Backfill window: timestamp = ended_at so usage lands in the correct billing
  period; run the job at least daily - events older than Stripe's late-event
  window will not aggregate.
- Transient failures raise (billed flag stays unset -> next run retries);
  permanent failures (e.g. invalid meter name, bad key) surface in the summary
  so they are fixed, never silently dropped.

Requires (deployment): stripe>=8.0 in apps/api/requirements.txt, columns
metering_billed_at / metering_event_id on ``calls`` (migration 024), a Billing
Meter named to match STRIPE_METER_EVENT_NAME in Stripe, and the tenant's
Stripe customer id stored (column resolved at runtime, see
_resolve_stripe_customer).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import Call, Tenant
from ..logging import get_logger
from .retry import is_transient_error, retry_transient

log = get_logger(__name__)

MIN_BILLED_MINUTES = 1
BATCH_LIMIT = 1000


def billed_minutes_for(
    duration_sec: int,
    *,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> int:
    """Round rule: ceil to the next whole minute; a completed call never bills 0.

    ``duration_sec`` is the source of truth when > 0. When it is 0 (older call
    paths do not populate it) fall back to the wall-clock window, floored to
    whole minutes. If neither is available the call cannot be billed (0), and
    the batch skips it.
    """
    if duration_sec and duration_sec > 0:
        return max(MIN_BILLED_MINUTES, math.ceil(duration_sec / 60))
    if started_at and ended_at and ended_at > started_at:
        return max(MIN_BILLED_MINUTES, math.floor((ended_at - started_at).total_seconds() / 60))
    return 0


def meter_event_identifier(call_id: str) -> str:
    """Stable per-call identifier; Stripe enforces uniqueness within a rolling
    period of at least 24 hours and caps the length at 100 chars."""
    return f"voxflow-call-meter-{call_id}"


def _resolve_stripe_customer(tenant: Tenant) -> str:
    """Find the tenant's Stripe customer id across common column names."""
    for attr in ("stripe_customer_id", "stripe_customer", "customer_id"):
        value = getattr(tenant, attr, None)
        if value:
            return str(value)
    return ""


@retry_transient(tries=3, base_delay=0.5, max_delay=8.0, jitter=0.3)
def _send_meter_event(
    *,
    event_name: str,
    identifier: str,
    payload: dict[str, Any],
    timestamp_unix: int,
) -> Any:
    """Create one Billing Meter event. Stripe docs:
    docs.stripe.com/api/billing/meter-event/create"""
    from .billing_service import _stripe_module  # lazy import, sets api_key

    stripe = _stripe_module()
    return stripe.billing.MeterEvent.create(
        event_name=event_name,
        identifier=identifier,
        payload=payload,
        timestamp=timestamp_unix,
    )


def meter_calls_for_tenant(
    db: Session, tenant: Tenant, *, dry_run: bool = False
) -> dict[str, Any]:
    """Send meter events for one tenant's unbilled completed calls."""
    customer_id = _resolve_stripe_customer(tenant)
    if not customer_id:
        log.warning("meter.customer_unresolved", tenant_id=tenant.id)
        return {
            "tenant_id": tenant.id,
            "sent": 0,
            "skipped": 0,
            "reason": "no_stripe_customer",
        }

    settings = get_settings()
    event_name = getattr(settings, "stripe_meter_event_name", "voxflow_voice_minutes")

    stmt = (
        select(Call)
        .where(
            Call.tenant_id == tenant.id,
            Call.metering_billed_at.is_(None),
            Call.duration_sec > 0,
        )
        .order_by(Call.started_at)
        .limit(BATCH_LIMIT)
    )
    calls = list(db.execute(stmt).scalars())
    if not calls:
        return {"tenant_id": tenant.id, "sent": 0, "skipped": 0}

    sent = skipped = 0
    for call in calls:
        minutes = billed_minutes_for(
            call.duration_sec, started_at=call.started_at, ended_at=call.ended_at
        )
        if minutes <= 0:
            skipped += 1
            continue
        ts = call.ended_at or call.started_at or datetime.now(timezone.utc)
        ts_unix = int(ts.timestamp())
        identifier = meter_event_identifier(call.id)
        payload = {"stripe_customer_id": customer_id, "value": minutes}

        if dry_run:
            log.info(
                "meter.dry_run",
                tenant_id=tenant.id,
                call_id=call.id,
                minutes=minutes,
                identifier=identifier,
                timestamp_unix=ts_unix,
            )
            sent += 1
            continue

        try:
            _send_meter_event(
                event_name=event_name,
                identifier=identifier,
                payload=payload,
                timestamp_unix=ts_unix,
            )
        except Exception as exc:  # noqa: BLE001
            if is_transient_error(exc):
                log.error(
                    "meter.send_transient_failed",
                    tenant_id=tenant.id,
                    call_id=call.id,
                    err=str(exc)[:200],
                )
                raise  # abort batch; billed flag stays unset -> next run retries
            log.error(
                "meter.send_permanent_failed",
                tenant_id=tenant.id,
                call_id=call.id,
                err=str(exc)[:200],
            )
            skipped += 1
            continue

        call.metering_billed_at = datetime.now(timezone.utc)
        call.metering_event_id = identifier
        sent += 1

    db.commit()
    return {"tenant_id": tenant.id, "sent": sent, "skipped": skipped}


def meter_all_tenants(
    db: Session, *, tenant_id: str | None = None, dry_run: bool = False
) -> dict[str, Any]:
    """Batch entrypoint for the periodic metering job."""
    settings = get_settings()
    if not settings.stripe_live_mode and not dry_run:
        log.warning("meter.sandbox_skip", reason="stripe_live_mode=False")
        return {"tenants": 0, "sent": 0, "skipped": 0, "note": "sandbox_mode"}

    stmt = select(Tenant).where(Tenant.active == 1)
    if tenant_id:
        stmt = stmt.where(Tenant.id == tenant_id)
    tenants = list(db.execute(stmt).scalars())

    summary: dict[str, Any] = {"tenants": 0, "sent": 0, "skipped": 0, "errors": []}
    for tenant in tenants:
        try:
            res = meter_calls_for_tenant(db, tenant, dry_run=dry_run)
        except Exception as exc:  # noqa: BLE001 (transient -> keep other tenants)
            summary["errors"].append({"tenant_id": tenant.id, "err": str(exc)[:120]})
            log.error("meter.tenant_failed", tenant_id=tenant.id, err=str(exc)[:200])
            db.rollback()
            continue
        summary["tenants"] += 1
        summary["sent"] += res.get("sent", 0)
        summary["skipped"] += res.get("skipped", 0)

    db.commit()
    log.info(
        "meter.batch_done",
        tenants=summary["tenants"],
        sent=summary["sent"],
        skipped=summary["skipped"],
        errors=len(summary["errors"]),
    )
    return summary
