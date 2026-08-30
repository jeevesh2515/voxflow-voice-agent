"""Day 51 tenant-scoped observability, call-KPI, and alerting endpoints.

Every route resolves authorization from the application-owned ``tenant_members``
ledger before it touches tenant data. Read routes accept any active member role
(including the fixed read-only demo viewer); the alert-test route is owner-only
because it enqueues durable outbound work.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ..auth import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER, require_tenant_role
from ..db import Tenant, session_scope
from ..services.alerting_service import (
    alert_channels,
    dispatch_alert_notification,
    evaluate_alerts,
    get_alert_thresholds,
    set_alert_thresholds,
)
from ..services.observability_service import (
    MAX_EVENT_LIMIT,
    MAX_RANGE_DAYS,
    get_call_kpis,
    get_recent_system_events,
    get_system_health_metrics,
)


router = APIRouter(prefix="/api/tenants/{tenant_id}/observability", tags=["observability"])

READ_ROLES = {ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER}


class AlertThresholdsIn(BaseModel):
    escalation_rate_pct: float | None = Field(default=None, ge=0, le=100)
    sla_breach_count: float | None = Field(default=None, ge=0)
    p90_latency_ms: float | None = Field(default=None, ge=0)
    error_rate_pct: float | None = Field(default=None, ge=0, le=100)


def _tenant_not_found(exc: ValueError) -> HTTPException:
    if "tenant_not_found" in str(exc):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/kpis")
def tenant_observability_kpis(
    request: Request,
    tenant_id: str,
    days: int = Query(default=7, ge=1, le=MAX_RANGE_DAYS),
) -> dict[str, Any]:
    """Return call KPIs, latency percentiles, daily volume, and category breakdowns."""

    with session_scope() as db:
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles=READ_ROLES, allow_demo=True)
        try:
            return get_call_kpis(db, tenant_id, time_range_days=days)
        except ValueError as exc:
            raise _tenant_not_found(exc) from exc


@router.get("/health")
def tenant_observability_health(request: Request, tenant_id: str) -> dict[str, Any]:
    """Return subsystem diagnostic latencies and durable-work health for one tenant."""

    with session_scope() as db:
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles=READ_ROLES, allow_demo=True)
        try:
            return get_system_health_metrics(db, tenant_id)
        except ValueError as exc:
            raise _tenant_not_found(exc) from exc


@router.get("/events")
def tenant_observability_events(
    request: Request,
    tenant_id: str,
    limit: int = Query(default=20, ge=1, le=MAX_EVENT_LIMIT),
) -> dict[str, Any]:
    """Return a merged, PII-scrubbed stream of recent tenant operational events."""

    with session_scope() as db:
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles=READ_ROLES, allow_demo=True)
        try:
            return get_recent_system_events(db, tenant_id, limit=limit)
        except ValueError as exc:
            raise _tenant_not_found(exc) from exc


@router.get("/alerts")
def tenant_observability_alerts(
    request: Request,
    tenant_id: str,
    days: int = Query(default=7, ge=1, le=MAX_RANGE_DAYS),
) -> dict[str, Any]:
    """Evaluate configured thresholds and return the in-app alert badge payload."""

    with session_scope() as db:
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles=READ_ROLES, allow_demo=True)
        try:
            kpis = get_call_kpis(db, tenant_id, time_range_days=days)
            health = get_system_health_metrics(db, tenant_id)
        except ValueError as exc:
            raise _tenant_not_found(exc) from exc
        thresholds = get_alert_thresholds(db, tenant_id)
        evaluation = evaluate_alerts(tenant_id=tenant_id, kpis=kpis, health=health, thresholds=thresholds)
        tenant = db.get(Tenant, tenant_id)
        evaluation["channels"] = alert_channels(tenant) if tenant else {}
        return evaluation


@router.put("/alerts/thresholds")
def update_tenant_alert_thresholds(
    request: Request,
    tenant_id: str,
    payload: AlertThresholdsIn,
) -> dict[str, Any]:
    """Persist tenant alert threshold overrides. Owner-only configuration change."""

    with session_scope() as db:
        actor = require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
        if actor.is_demo:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="demo_access_read_only")
        if db.get(Tenant, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        try:
            thresholds = set_alert_thresholds(db, tenant_id, payload.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return {"ok": True, "tenant_id": tenant_id, "thresholds": thresholds}


@router.post("/alerts/test")
def trigger_tenant_test_alert(request: Request, tenant_id: str) -> dict[str, Any]:
    """Enqueue one durable test alert notification. Owner-only.

    The notification is queued for the feature-gated worker, so this endpoint
    proves the routing configuration without the API process sending mail or
    calling a customer webhook itself.
    """

    with session_scope() as db:
        actor = require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
        if actor.is_demo:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="demo_access_read_only")
        try:
            kpis = get_call_kpis(db, tenant_id, time_range_days=7)
            health = get_system_health_metrics(db, tenant_id)
        except ValueError as exc:
            raise _tenant_not_found(exc) from exc

        thresholds = get_alert_thresholds(db, tenant_id)
        evaluation = evaluate_alerts(tenant_id=tenant_id, kpis=kpis, health=health, thresholds=thresholds)
        try:
            receipt = dispatch_alert_notification(
                db,
                tenant_id=tenant_id,
                evaluation=evaluation,
                reason="operator_test",
            )
        except ValueError as exc:
            raise _tenant_not_found(exc) from exc
        return {"ok": True, "tenant_id": tenant_id, "evaluation": evaluation, "dispatch": receipt}
