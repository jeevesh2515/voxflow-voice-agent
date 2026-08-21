"""Day 35 controlled-pilot readiness domain service.

The module is intentionally separate from HTTP handlers and worker start-up.
It can evaluate a tenant's written readiness contract, reject non-cohort targets,
produce a read-only rollback preview, and execute a database-only rollback only
when an operator invokes it from a trusted operational workflow. It never starts
workers, changes provider settings, or calls an external service.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from sqlalchemy.orm import Session

from .config import get_settings
from .db import (
    Call,
    CampaignQueue,
    JobRun,
    PilotCohortMember,
    PilotConfiguration,
    PilotSecurityIncident,
)
from .jobs.staging import (
    durable_campaign_dry_run,
    durable_campaign_worker_enabled,
    durable_side_effects_dry_run,
    durable_side_effects_worker_enabled,
)


PILOT_METRIC_CONTRACT: dict[str, dict[str, str]] = {
    "successful_call_completion": {
        "formula": "completed terminal cohort targets / initiated cohort targets",
        "denominator": "cohort targets with at least one dispatch attempt and a non-cancelled terminal/active status",
        "exclusions": "cancelled-before-dispatch targets and targets outside the approved cohort",
        "source": "campaign_queue",
    },
    "escalation_rate": {
        "formula": "cohort calls marked escalated / eligible answered cohort calls",
        "denominator": "cohort calls with an answered or completed target state",
        "exclusions": "no-answer, cancelled-before-dispatch, and non-cohort calls",
        "source": "calls plus campaign_queue",
    },
    "first_call_resolution": {
        "formula": "eligible cohort calls resolved without an escalation or later follow-up / eligible answered cohort calls",
        "denominator": "cohort calls with an answered or completed target state",
        "exclusions": "no-answer, cancelled-before-dispatch, non-cohort calls, and unresolved follow-ups",
        "source": "calls plus campaign_queue",
    },
    "security_incidents": {
        "formula": "count of confirmed pilot security incident records",
        "denominator": "not applicable; a count is reported for the approved pilot period",
        "exclusions": "suspected-but-unconfirmed records and incidents outside the pilot identifier",
        "source": "pilot_security_incidents",
    },
}


@dataclass(frozen=True)
class PilotAdmission:
    decision: str
    reason_code: str
    evidence: dict[str, object]


def hash_recipient(phone: str) -> str:
    """Return the stable, non-reversible cohort matching key for an E.164 number."""

    return sha256(phone.strip().encode("utf-8")).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ratio(numerator: int, denominator: int) -> dict[str, float | int | None]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": round(numerator / denominator, 4) if denominator else None,
    }


def _approved_members(db: Session, *, tenant_id: str, cohort_id: str) -> list[PilotCohortMember]:
    return (
        db.query(PilotCohortMember)
        .filter(
            PilotCohortMember.tenant_id == tenant_id,
            PilotCohortMember.cohort_id == cohort_id,
            PilotCohortMember.status == "approved",
        )
        .all()
    )


def evaluate_pilot_admission(
    db: Session,
    *,
    tenant_id: str,
    recipient_phone: str,
    now: datetime,
) -> PilotAdmission:
    """Fail closed before any dispatch capacity or provider operation is reserved."""

    settings = get_settings()
    if not settings.pilot_readiness_enforced:
        return PilotAdmission("allowed", "pilot_gate_test_bypass", {"enforced": False})
    if tenant_id not in settings.pilot_readiness_approved_tenant_ids:
        return PilotAdmission("cancelled", "pilot_tenant_not_approved", {"tenant_id": tenant_id})

    config = db.get(PilotConfiguration, tenant_id)
    if config is None:
        return PilotAdmission("cancelled", "pilot_configuration_missing", {"tenant_id": tenant_id})
    if config.status != "approved":
        return PilotAdmission("cancelled", "pilot_not_approved", {"status": config.status})
    if _as_utc(config.expires_at) is None or _as_utc(config.expires_at) <= _as_utc(now):
        return PilotAdmission("cancelled", "pilot_expired", {"pilot_id": config.pilot_id})
    if not config.primary_escalation_owner or not config.backup_escalation_owner or not config.approved_by:
        return PilotAdmission("cancelled", "pilot_escalation_or_approval_missing", {"pilot_id": config.pilot_id})
    if config.cohort_size < 1 or config.daily_call_limit < 1 or config.max_in_flight != 1:
        return PilotAdmission(
            "cancelled",
            "pilot_capacity_invalid",
            {
                "cohort_size": config.cohort_size,
                "daily_call_limit": config.daily_call_limit,
                "max_in_flight": config.max_in_flight,
            },
        )

    approved_members = _approved_members(db, tenant_id=tenant_id, cohort_id=config.cohort_id)
    if len(approved_members) != config.cohort_size:
        return PilotAdmission(
            "cancelled",
            "pilot_cohort_review_incomplete",
            {"configured_cohort_size": config.cohort_size, "approved_member_count": len(approved_members)},
        )
    recipient_hash = hash_recipient(recipient_phone)
    if recipient_hash not in {member.recipient_hash for member in approved_members}:
        return PilotAdmission("cancelled", "pilot_cohort_mismatch", {"pilot_id": config.pilot_id})

    # Day 36 adds an independent final hold point. A green readiness scorecard
    # never authorises a dispatch: the current pilot version needs a fresh,
    # trusted same-cohort review decision. The helper only reads persisted
    # evidence; it cannot enable a worker, change a tenant, or expand capacity.
    from .pilot_operations import pilot_operations_hold_allows_dispatch

    hold_allowed, hold_reason, hold_evidence = pilot_operations_hold_allows_dispatch(
        db,
        config=config,
        now=now,
    )
    if not hold_allowed:
        return PilotAdmission("cancelled", hold_reason, hold_evidence)
    return PilotAdmission(
        "allowed",
        "pilot_admission_allowed",
        {
            "pilot_id": config.pilot_id,
            "cohort_id": config.cohort_id,
            "metric_contract_version": config.metric_contract_version,
            "expires_at": _as_utc(config.expires_at).isoformat(),
        },
    )


def _pilot_target_rows(db: Session, config: PilotConfiguration) -> list[CampaignQueue]:
    approved_hashes = {
        member.recipient_hash
        for member in _approved_members(db, tenant_id=config.tenant_id, cohort_id=config.cohort_id)
    }
    if not approved_hashes:
        return []
    return [
        target
        for target in db.query(CampaignQueue).filter(CampaignQueue.tenant_id == config.tenant_id).all()
        if hash_recipient(target.recipient_phone) in approved_hashes
    ]


def rollback_preview(db: Session, *, tenant_id: str) -> dict[str, object]:
    """Return a read-only, job-precise rollback plan with no database mutation."""

    config = db.get(PilotConfiguration, tenant_id)
    if config is None:
        return {"configured": False, "tenant_id": tenant_id, "can_execute": False, "reason": "pilot_configuration_missing"}

    targets = _pilot_target_rows(db, config)
    target_ids = {target.id for target in targets}
    candidate_jobs: list[JobRun] = []
    active_claims: list[JobRun] = []
    for job in db.query(JobRun).filter(JobRun.tenant_id == tenant_id, JobRun.job_type == "campaign.target.dispatch").all():
        try:
            queue_id = str(json.loads(job.payload_json).get("campaign_queue_id", ""))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if queue_id not in target_ids:
            continue
        if job.status in {"ready", "retry_scheduled"}:
            candidate_jobs.append(job)
        elif job.status == "running":
            active_claims.append(job)

    workers_disabled = not durable_campaign_worker_enabled()
    return {
        "configured": True,
        "tenant_id": tenant_id,
        "pilot_id": config.pilot_id,
        "pilot_status": config.status,
        "worker_disabled": workers_disabled,
        "active_claim_count": len(active_claims),
        "would_cancel_job_count": len(candidate_jobs),
        "would_cancel_target_count": len({job_id for job_id in target_ids}),
        "would_cancel_job_ids": [job.id for job in candidate_jobs],
        "can_execute": bool(workers_disabled and not active_claims and config.status in {"approved", "paused"}),
        "execution_guard": "Requires a trusted direct-service invocation; no HTTP activation or rollback endpoint exists.",
    }


def execute_database_only_rollback(db: Session, *, tenant_id: str, confirmed_by: str, now: datetime) -> dict[str, object]:
    """Durably cancel unclaimed pilot jobs after a human-confirmed rollback.

    The method never contacts a provider. It refuses to proceed if a campaign
    worker is enabled or any pilot job has an active claim, preventing a false
    claim that a rollback drained work it did not own.
    """

    if not confirmed_by.strip():
        raise ValueError("confirmed_by is required for a pilot rollback")
    preview = rollback_preview(db, tenant_id=tenant_id)
    if not preview.get("configured"):
        raise ValueError("pilot configuration is missing")
    if not preview.get("can_execute"):
        raise ValueError("rollback preconditions are not satisfied")

    config = db.get(PilotConfiguration, tenant_id)
    assert config is not None
    job_ids = set(preview["would_cancel_job_ids"])
    target_rows = _pilot_target_rows(db, config)
    target_by_id = {target.id: target for target in target_rows}
    cancelled = 0
    for job in db.query(JobRun).filter(JobRun.id.in_(job_ids)).all() if job_ids else []:
        try:
            queue_id = str(json.loads(job.payload_json).get("campaign_queue_id", ""))
        except (TypeError, ValueError, json.JSONDecodeError):
            queue_id = ""
        job.status = "cancelled"
        job.last_error_code = "pilot_rollback"
        job.last_error_json = json.dumps({"confirmed_by": confirmed_by.strip(), "at": _as_utc(now).isoformat()})
        job.finished_at = now
        target = target_by_id.get(queue_id)
        if target is not None:
            target.status = "cancelled"
            target.next_retry_at = None
            target.transcript_summary = "Day 35 pilot rollback before provider dispatch."
        cancelled += 1
    config.status = "rolled_back"
    config.updated_at = now
    db.flush()
    return {"tenant_id": tenant_id, "pilot_id": config.pilot_id, "cancelled_job_count": cancelled, "worker_disabled": True, "external_calls": 0}


def pilot_scorecard(db: Session, *, tenant_id: str, now: datetime | None = None) -> dict[str, Any]:
    """Build a redacted readiness and measurement scorecard for one tenant."""

    now = _as_utc(now or datetime.now(timezone.utc))
    config = db.get(PilotConfiguration, tenant_id)
    if config is None:
        return {
            "tenant_id": tenant_id,
            "configured": False,
            "readiness": {"state": "blocked", "blocking_reasons": ["pilot_configuration_missing"]},
            "metric_contract": PILOT_METRIC_CONTRACT,
            "metrics": {},
            "rollback": rollback_preview(db, tenant_id=tenant_id),
        }

    approved_members = _approved_members(db, tenant_id=tenant_id, cohort_id=config.cohort_id)
    target_rows = _pilot_target_rows(db, config)
    approved_hashes = {member.recipient_hash for member in approved_members}
    initiated_statuses = {"dialing", "answered", "completed", "failed", "no_answer"}
    answered_statuses = {"answered", "completed"}
    initiated = [target for target in target_rows if target.attempts_made > 0 and target.status in initiated_statuses]
    completed = [target for target in initiated if target.status == "completed"]
    answered_hashes = {hash_recipient(target.recipient_phone) for target in target_rows if target.status in answered_statuses}
    cohort_calls = [
        call
        for call in db.query(Call).filter(Call.tenant_id == tenant_id).all()
        if hash_recipient(call.caller_phone) in approved_hashes and hash_recipient(call.caller_phone) in answered_hashes
    ]
    escalated = [call for call in cohort_calls if bool(call.escalated)]
    fcr = [
        call
        for call in cohort_calls
        if call.resolution_status == "resolved" and not bool(call.follow_up_required) and not bool(call.escalated)
    ]
    confirmed_incidents = (
        db.query(PilotSecurityIncident)
        .filter(
            PilotSecurityIncident.tenant_id == tenant_id,
            PilotSecurityIncident.pilot_id == config.pilot_id,
            PilotSecurityIncident.status == "confirmed",
        )
        .count()
    )

    blocking_reasons: list[str] = []
    settings = get_settings()
    if tenant_id not in settings.pilot_readiness_approved_tenant_ids:
        blocking_reasons.append("pilot_tenant_not_environment_approved")
    if config.status != "approved":
        blocking_reasons.append(f"pilot_status_{config.status}")
    if _as_utc(config.expires_at) <= now:
        blocking_reasons.append("pilot_expired")
    if not config.primary_escalation_owner or not config.backup_escalation_owner or not config.approved_by:
        blocking_reasons.append("pilot_human_approval_or_coverage_missing")
    if config.max_in_flight != 1 or config.daily_call_limit < 1 or config.cohort_size < 1:
        blocking_reasons.append("pilot_capacity_invalid")
    if len(approved_members) != config.cohort_size:
        blocking_reasons.append("pilot_cohort_review_incomplete")
    if durable_campaign_worker_enabled() or durable_side_effects_worker_enabled():
        blocking_reasons.append("worker_must_remain_disabled_for_readiness_review")
    if not durable_campaign_dry_run() or not durable_side_effects_dry_run():
        blocking_reasons.append("dry_run_must_remain_enabled_for_readiness_review")

    return {
        "tenant_id": tenant_id,
        "configured": True,
        "pilot": {
            "pilot_id": config.pilot_id,
            "version": config.version,
            "status": config.status,
            "cohort_id": config.cohort_id,
            "cohort_size": config.cohort_size,
            "approved_member_count": len(approved_members),
            "timezone_name": config.timezone_name,
            "calling_window_start": config.calling_window_start,
            "calling_window_end": config.calling_window_end,
            "daily_call_limit": config.daily_call_limit,
            "max_in_flight": config.max_in_flight,
            "expires_at": _as_utc(config.expires_at).isoformat(),
            "primary_escalation_owner": config.primary_escalation_owner,
            "backup_escalation_owner": config.backup_escalation_owner,
            "acknowledgement_timeout_minutes": config.acknowledgement_timeout_minutes,
            "metric_contract_version": config.metric_contract_version,
            "approved_by": config.approved_by,
        },
        "readiness": {
            "state": "ready_for_review" if not blocking_reasons else "blocked",
            "blocking_reasons": blocking_reasons,
            "workers": {
                "campaign_worker_enabled": durable_campaign_worker_enabled(),
                "campaign_dry_run": durable_campaign_dry_run(),
                "side_effect_worker_enabled": durable_side_effects_worker_enabled(),
                "side_effect_dry_run": durable_side_effects_dry_run(),
            },
        },
        "metric_contract": PILOT_METRIC_CONTRACT,
        "metrics": {
            "successful_call_completion": _ratio(len(completed), len(initiated)),
            "escalation_rate": _ratio(len(escalated), len(cohort_calls)),
            "first_call_resolution": _ratio(len(fcr), len(cohort_calls)),
            "security_incidents": {"confirmed_count": confirmed_incidents, "objective": 0},
        },
        "rollback": rollback_preview(db, tenant_id=tenant_id),
    }
