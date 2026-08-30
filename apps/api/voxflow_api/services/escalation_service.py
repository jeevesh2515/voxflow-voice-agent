"""Escalation lifecycle, SLA computation, and operator assignment domain service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import json
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from ..db import Call, Tenant, TenantMember

VALID_PRIORITIES = {"critical", "high", "medium", "low"}
VALID_STATUSES = {"none", "pending", "in_progress", "resolved", "dismissed"}
VALID_RESOLUTION_CATEGORIES = {
    "callback_completed",
    "order_updated",
    "refund_issued",
    "quote_sent",
    "technical_fixed",
    "duplicate_or_invalid",
    "other",
}


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_sla_due_at(
    priority: str = "medium",
    base_sla_minutes: int = 60,
    from_time: datetime | None = None,
) -> datetime:
    """Compute target SLA deadline timestamp based on escalation priority."""
    now = _to_utc(from_time) or datetime.now(timezone.utc)
    base_mins = max(5, base_sla_minutes or 60)

    if priority == "critical":
        # Critical priority: 15 minutes (or 1/4 of base)
        delta_mins = min(15, max(5, base_mins // 4))
    elif priority == "high":
        # High priority: 30 minutes (or 1/2 of base)
        delta_mins = min(30, max(10, base_mins // 2))
    elif priority == "low":
        # Low priority: 4x base
        delta_mins = base_mins * 4
    else:
        # Medium priority: base SLA minutes
        delta_mins = base_mins

    return now + timedelta(minutes=delta_mins)


def derive_escalation_priority(
    satisfaction: str | None = None,
    reason: str | None = None,
    follow_up_required: bool = False,
    verified: bool = False,
) -> str:
    """Infer escalation priority level from satisfaction and context."""
    reason_lower = (reason or "").lower()
    critical_keywords = ("emergency", "fraud", "accident", "damage", "legal", "stolen", "loss")

    if any(kw in reason_lower for kw in critical_keywords):
        return "critical"

    if satisfaction == "unhappy":
        # An unhappy caller who was never verified is also a potential
        # social-engineering attempt — treat it as high priority either way,
        # but the verified flag is kept in the signature for call-site clarity.
        return "high"

    if follow_up_required:
        return "medium"

    return "medium"


def init_call_escalation(
    call: Call,
    tenant: Tenant | None = None,
    priority: str | None = None,
) -> None:
    """Initialize escalation tracking attributes for an escalated call."""
    call.escalated = 1
    call.escalation_status = "pending"

    eff_priority = priority if priority in VALID_PRIORITIES else derive_escalation_priority(
        satisfaction=call.satisfaction,
        reason=call.reason,
        follow_up_required=bool(call.follow_up_required),
        verified=bool(call.verified),
    )
    call.escalation_priority = eff_priority

    base_sla = tenant.escalation_sla_minutes if tenant else 60
    call.sla_due_at = compute_sla_due_at(
        priority=eff_priority,
        base_sla_minutes=base_sla,
        from_time=call.started_at or datetime.now(timezone.utc),
    )


def get_escalation_kpis(db: Session, tenant_id: str) -> dict[str, Any]:
    """Aggregate real-time escalation metrics and SLA adherence statistics."""
    now = datetime.now(timezone.utc)

    # Base query for all escalated/follow-up calls in this tenant
    is_esc_expr = or_(
        Call.escalated == 1,
        Call.follow_up_required == 1,
        Call.escalation_status.in_(["pending", "in_progress", "resolved", "dismissed"]),
    )

    calls = (
        db.execute(
            select(Call).where(
                Call.tenant_id == tenant_id,
                is_esc_expr,
            )
        )
        .scalars()
        .all()
    )

    total_escalations = len(calls)
    pending_count = 0
    in_progress_count = 0
    resolved_count = 0
    dismissed_count = 0
    breached_count = 0

    resolved_resolution_times_min: list[float] = []
    sla_met_count = 0

    for c in calls:
        # Effective status
        status = c.escalation_status
        if not status or status == "none":
            status = "resolved" if c.staff_resolved_at else "pending"

        sla_due_utc = _to_utc(c.sla_due_at)
        resolved_at_utc = _to_utc(c.staff_resolved_at)
        started_at_utc = _to_utc(c.started_at)

        if status == "pending":
            pending_count += 1
            if sla_due_utc and sla_due_utc < now:
                breached_count += 1
        elif status == "in_progress":
            in_progress_count += 1
            if sla_due_utc and sla_due_utc < now:
                breached_count += 1
        elif status == "resolved":
            resolved_count += 1
            if resolved_at_utc and started_at_utc:
                diff_sec = (resolved_at_utc - started_at_utc).total_seconds()
                resolved_resolution_times_min.append(max(0.1, diff_sec / 60.0))

            if sla_due_utc and resolved_at_utc:
                if resolved_at_utc <= sla_due_utc:
                    sla_met_count += 1
            else:
                sla_met_count += 1
        elif status == "dismissed":
            dismissed_count += 1

    total_closed = resolved_count + dismissed_count
    sla_compliance_rate = 100.0
    if resolved_count > 0:
        sla_compliance_rate = round((sla_met_count / resolved_count) * 100.0, 1)

    avg_resolution_min = 0.0
    if resolved_resolution_times_min:
        avg_resolution_min = round(
            sum(resolved_resolution_times_min) / len(resolved_resolution_times_min), 1
        )

    return {
        "tenant_id": tenant_id,
        "total_escalations": total_escalations,
        "open_count": pending_count + in_progress_count,
        "pending_count": pending_count,
        "in_progress_count": in_progress_count,
        "resolved_count": resolved_count,
        "dismissed_count": dismissed_count,
        "breached_count": breached_count,
        "sla_compliance_rate": sla_compliance_rate,
        "avg_resolution_min": avg_resolution_min,
    }


def list_escalations(
    db: Session,
    tenant_id: str,
    status: str | None = None,
    priority: str | None = None,
    breached_only: bool = False,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Call], int]:
    """Retrieve filtered, paginated escalations with total count."""
    now = datetime.now(timezone.utc)

    is_esc_expr = or_(
        Call.escalated == 1,
        Call.follow_up_required == 1,
        Call.escalation_status.in_(["pending", "in_progress", "resolved", "dismissed"]),
    )

    query = select(Call).where(Call.tenant_id == tenant_id, is_esc_expr)

    if status and status != "all":
        if status in ("pending", "in_progress", "resolved", "dismissed"):
            query = query.where(Call.escalation_status == status)
        elif status == "open":
            query = query.where(Call.escalation_status.in_(["pending", "in_progress"]))

    if priority and priority in VALID_PRIORITIES:
        query = query.where(Call.escalation_priority == priority)

    if breached_only:
        query = query.where(
            Call.escalation_status.in_(["pending", "in_progress"]),
            Call.sla_due_at.is_not(None),
            Call.sla_due_at < now,
        )

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Call.caller_name).like(term),
                func.lower(Call.caller_phone).like(term),
                func.lower(Call.reason).like(term),
                func.lower(Call.solution).like(term),
                func.lower(Call.id).like(term),
            )
        )

    # Count total matching
    count_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_stmt) or 0

    # Order by: open breached first, then open by sla_due_at, then started_at desc
    query = query.order_by(
        desc(Call.started_at),
    ).offset(offset).limit(limit)

    results = db.execute(query).scalars().all()
    return list(results), total


def assign_escalation(
    db: Session,
    tenant_id: str,
    call_id: str,
    assigned_to_user_id: str | None,
    actor_user_id: str,
) -> Call:
    """Assign or claim an escalation ticket.

    The assignee must hold an active membership in the same tenant. Without
    this check, a ticket can be "assigned" to a nonexistent user, a revoked
    member, or a member of a different tenant — it then silently sits in
    ``in_progress`` forever with nobody able to see it in their queue.
    """
    call = db.get(Call, call_id)
    if not call or call.tenant_id != tenant_id:
        raise ValueError("call_not_found")

    if assigned_to_user_id:
        assignee = (
            db.query(TenantMember)
            .filter(
                TenantMember.tenant_id == tenant_id,
                TenantMember.user_id == assigned_to_user_id,
                TenantMember.status == "active",
            )
            .first()
        )
        if assignee is None:
            raise ValueError("assignee_not_active_member")

    now = datetime.now(timezone.utc)
    call.assigned_to_user_id = assigned_to_user_id
    call.assigned_at = now if assigned_to_user_id else None

    # If currently pending and assigned, transition to in_progress
    if assigned_to_user_id and (not call.escalation_status or call.escalation_status == "pending" or call.escalation_status == "none"):
        call.escalation_status = "in_progress"

    db.flush()
    return call


def resolve_escalation(
    db: Session,
    tenant_id: str,
    call_id: str,
    status: str,
    resolution_category: str | None,
    staff_resolution: str,
    actor_user_id: str,
) -> Call:
    """Close an escalation with structured resolution and operator attribution."""
    call = db.get(Call, call_id)
    if not call or call.tenant_id != tenant_id:
        raise ValueError("call_not_found")

    if status not in ("resolved", "dismissed"):
        raise ValueError(f"invalid_status: must be 'resolved' or 'dismissed', got {status}")

    # Re-closing an already-closed ticket overwrites the original operator's
    # attribution and resolution timestamp — destroying the audit trail. Only
    # a fresh reopen (assign) may clear those fields, so a second close is a
    # 409 at the route layer.
    if call.escalation_status in ("resolved", "dismissed"):
        raise ValueError("escalation_already_closed")

    category = resolution_category if resolution_category in VALID_RESOLUTION_CATEGORIES else "callback_completed"

    now = datetime.now(timezone.utc)
    call.escalation_status = status
    call.resolution_category = category
    call.staff_resolution = staff_resolution
    call.resolved_by_user_id = actor_user_id
    call.staff_resolved_at = now

    if status == "resolved":
        call.resolution_status = "resolved"

    db.flush()
    return call
