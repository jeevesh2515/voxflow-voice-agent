"""Tenant-scoped campaign dispatch policy controls for Day 30."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..pilot_readiness import evaluate_pilot_admission
from ..db import (
    CampaignDispatchReservation,
    CampaignPolicyDecision,
    CampaignQueue,
    OutboundCampaign,
    RecipientCampaignPreference,
    TenantCampaignPolicy,
    TenantDailyDispatchUsage,
)


@dataclass(frozen=True)
class PolicyDecision:
    """A deterministic dispatch-policy result with auditable evidence."""

    decision: str  # allowed | deferred | cancelled
    reason_code: str
    evidence: dict[str, object]
    next_eligible_at: datetime | None = None


def _parse_clock(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":", 1))
    return time(hour=hour, minute=minute)


def _timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown IANA timezone {name!r}") from exc


def _inside_window(local_now: datetime, start: time, end: time) -> bool:
    now_clock = local_now.timetz().replace(tzinfo=None)
    if start < end:
        return start <= now_clock < end
    if start > end:  # overnight window, for example 22:00 through 02:00
        return now_clock >= start or now_clock < end
    return False


def _next_window_start(local_now: datetime, start: time, end: time) -> datetime:
    """Return the first permitted local boundary strictly after an ineligible instant."""

    candidate_today = local_now.replace(
        hour=start.hour,
        minute=start.minute,
        second=0,
        microsecond=0,
    )
    if start < end:
        return candidate_today if local_now < candidate_today else candidate_today + timedelta(days=1)
    # For an overnight window the only ineligible period is [end, start).
    return candidate_today if local_now < candidate_today else candidate_today + timedelta(days=1)


def _local_midnight_after(local_now: datetime) -> datetime:
    next_day = local_now.date() + timedelta(days=1)
    return datetime.combine(next_day, time.min, tzinfo=local_now.tzinfo)


def evaluate_campaign_policy(
    db: Session,
    *,
    tenant_id: str,
    campaign: OutboundCampaign,
    target: CampaignQueue,
    now: datetime,
) -> PolicyDecision:
    """Evaluate non-provider campaign eligibility without performing a side effect."""

    policy = db.get(TenantCampaignPolicy, tenant_id)
    if policy is None:
        return PolicyDecision(
            "cancelled",
            "tenant_policy_missing",
            {"tenant_id": tenant_id},
        )
    if not policy.enabled:
        return PolicyDecision(
            "cancelled",
            "tenant_policy_disabled",
            {"tenant_id": tenant_id},
        )
    if campaign.status not in {"active", "running"}:
        return PolicyDecision(
            "cancelled",
            "campaign_not_active",
            {"campaign_status": campaign.status},
        )

    preference = (
        db.query(RecipientCampaignPreference)
        .filter(
            RecipientCampaignPreference.tenant_id == tenant_id,
            RecipientCampaignPreference.recipient_phone == target.recipient_phone,
        )
        .one_or_none()
    )
    if preference is None or preference.consent_status != "granted":
        return PolicyDecision(
            "cancelled",
            "consent_not_granted",
            {"consent_status": preference.consent_status if preference else "missing"},
        )
    if preference.opted_out:
        return PolicyDecision(
            "cancelled",
            "recipient_opted_out",
            {"source": preference.source},
        )
    if preference.consent_purpose not in {"outbound_campaign", campaign.campaign_type}:
        return PolicyDecision(
            "cancelled",
            "consent_purpose_mismatch",
            {"consent_purpose": preference.consent_purpose, "campaign_type": campaign.campaign_type},
        )

    # Day 35 adds a second, independent fail-closed admission boundary. It is
    # evaluated only after tenant ownership and consent have passed, and before
    # any time-window or capacity reservation can authorize a provider effect.
    pilot = evaluate_pilot_admission(
        db,
        tenant_id=tenant_id,
        recipient_phone=target.recipient_phone,
        now=now,
    )
    if pilot.decision != "allowed":
        return PolicyDecision(pilot.decision, pilot.reason_code, pilot.evidence)

    try:
        tz = _timezone(policy.timezone_name)
        start = _parse_clock(policy.calling_window_start)
        end = _parse_clock(policy.calling_window_end)
    except ValueError as exc:
        return PolicyDecision(
            "cancelled",
            "tenant_policy_invalid",
            {"detail": str(exc)},
        )
    if start == end or policy.daily_call_limit < 1 or policy.max_in_flight < 1:
        return PolicyDecision(
            "cancelled",
            "tenant_policy_invalid",
            {
                "calling_window_start": policy.calling_window_start,
                "calling_window_end": policy.calling_window_end,
                "daily_call_limit": policy.daily_call_limit,
                "max_in_flight": policy.max_in_flight,
            },
        )

    local_now = now.astimezone(tz)
    if not _inside_window(local_now, start, end):
        next_local = _next_window_start(local_now, start, end)
        return PolicyDecision(
            "deferred",
            "outside_calling_window",
            {
                "timezone": policy.timezone_name,
                "calling_window_start": policy.calling_window_start,
                "calling_window_end": policy.calling_window_end,
            },
            next_local.astimezone(timezone.utc),
        )

    return PolicyDecision(
        "allowed",
        "policy_allowed",
        {
            "timezone": policy.timezone_name,
            "local_date": local_now.date().isoformat(),
            "daily_call_limit": policy.daily_call_limit,
            "max_in_flight": policy.max_in_flight,
            "pilot": pilot.evidence,
        },
    )


def _locked_usage(db: Session, *, tenant_id: str, local_date: str) -> TenantDailyDispatchUsage:
    query = db.query(TenantDailyDispatchUsage).filter(
        TenantDailyDispatchUsage.tenant_id == tenant_id,
        TenantDailyDispatchUsage.local_date == local_date,
    )
    if db.get_bind().dialect.name != "sqlite":
        query = query.with_for_update()
    usage = query.one_or_none()
    if usage is not None:
        return usage

    usage = TenantDailyDispatchUsage(
        id=f"tdu-{tenant_id}-{local_date}",
        tenant_id=tenant_id,
        local_date=local_date,
    )
    try:
        with db.begin_nested():
            db.add(usage)
            db.flush()
    except IntegrityError:
        db.expire_all()
        return _locked_usage(db, tenant_id=tenant_id, local_date=local_date)
    return usage


def reserve_dispatch_capacity(
    db: Session,
    *,
    tenant_id: str,
    job_id: str,
    policy: TenantCampaignPolicy,
    now: datetime,
) -> PolicyDecision:
    """Atomically reserve one tenant-day budget and active-dispatch slot for a job."""

    tz = _timezone(policy.timezone_name)
    local_now = now.astimezone(tz)
    local_date = local_now.date().isoformat()
    existing = db.query(CampaignDispatchReservation).filter(CampaignDispatchReservation.job_id == job_id).one_or_none()
    if existing is not None:
        if existing.status == "active":
            return PolicyDecision("allowed", "capacity_already_reserved", {"local_date": existing.local_date})
        if existing.status == "settled":
            return PolicyDecision("cancelled", "capacity_reservation_settled", {"local_date": existing.local_date})

    usage = _locked_usage(db, tenant_id=tenant_id, local_date=local_date)
    if usage.reserved_calls >= policy.daily_call_limit:
        return PolicyDecision(
            "deferred",
            "daily_call_budget_exhausted",
            {"local_date": local_date, "reserved_calls": usage.reserved_calls, "daily_call_limit": policy.daily_call_limit},
            _local_midnight_after(local_now).astimezone(timezone.utc),
        )
    if usage.active_dispatches >= policy.max_in_flight:
        return PolicyDecision(
            "deferred",
            "tenant_concurrency_limited",
            {"local_date": local_date, "active_dispatches": usage.active_dispatches, "max_in_flight": policy.max_in_flight},
            now + timedelta(seconds=60),
        )

    usage.reserved_calls += 1
    usage.active_dispatches += 1
    db.add(
        CampaignDispatchReservation(
            id=f"cdr-{uuid.uuid4().hex[:20]}",
            job_id=job_id,
            tenant_id=tenant_id,
            local_date=local_date,
            status="active",
        )
    )
    db.flush()
    return PolicyDecision("allowed", "capacity_reserved", {"local_date": local_date})


def release_dispatch_capacity(db: Session, *, job_id: str, now: datetime) -> None:
    """Release an unattempted reservation after a policy deferral or cancellation."""

    reservation = db.query(CampaignDispatchReservation).filter(CampaignDispatchReservation.job_id == job_id).one_or_none()
    if reservation is None or reservation.status != "active":
        return
    usage = _locked_usage(db, tenant_id=reservation.tenant_id, local_date=reservation.local_date)
    usage.reserved_calls = max(0, usage.reserved_calls - 1)
    usage.active_dispatches = max(0, usage.active_dispatches - 1)
    reservation.status = "released"
    reservation.settled_at = now
    db.flush()


def settle_dispatch_capacity(db: Session, *, job_id: str, now: datetime) -> None:
    """Settle active capacity after a dry-run or terminal provider outcome."""

    reservation = db.query(CampaignDispatchReservation).filter(CampaignDispatchReservation.job_id == job_id).one_or_none()
    if reservation is None or reservation.status != "active":
        return
    usage = _locked_usage(db, tenant_id=reservation.tenant_id, local_date=reservation.local_date)
    usage.active_dispatches = max(0, usage.active_dispatches - 1)
    reservation.status = "settled"
    reservation.settled_at = now
    db.flush()


def record_policy_decision(
    db: Session,
    *,
    tenant_id: str,
    job_id: str,
    campaign_id: str,
    campaign_queue_id: str,
    result: PolicyDecision,
    now: datetime,
) -> None:
    """Append immutable, tenant-owned policy evidence for every evaluation."""

    db.add(
        CampaignPolicyDecision(
            id=f"cpd-{uuid.uuid4().hex[:20]}",
            tenant_id=tenant_id,
            job_id=job_id,
            campaign_id=campaign_id,
            campaign_queue_id=campaign_queue_id,
            decision=result.decision,
            reason_code=result.reason_code,
            evidence_json=json.dumps(result.evidence, sort_keys=True),
            next_eligible_at=result.next_eligible_at,
            created_at=now,
        )
    )
    db.flush()
