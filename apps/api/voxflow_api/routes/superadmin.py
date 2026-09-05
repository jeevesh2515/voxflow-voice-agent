"""Superadmin visibility: every tenant and the minutes each one used.

Phase 0 step 5 — free scaffolding, just code. Mounted at ``/api/superadmin``
(see ``main.py``), which is deliberately NOT under ``/api/admin``: the admin
router is tenant-scoped, this one is platform-scoped.

Authorization is one dependency: env allow-list (``PLATFORM_ADMIN_USER_IDS``)
OR an ``is_superadmin`` row that is still ``active``
(``auth.require_superadmin``). A single dependency at each route means a route
cannot forget the check — there is no unguarded path to add one to.

Minutes reuse ``metering_service.billed_minutes_for`` so the dashboard and the
billing meter can never disagree on what a minute is.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from ..auth import require_superadmin
from ..db import Call, Tenant, session_scope
from ..logging import get_logger
from ..services.metering_service import billed_minutes_for


log = get_logger(__name__)
router = APIRouter(prefix="/api/superadmin", tags=["superadmin"])


def _superadmin_guard(request: Request) -> Any:
    with session_scope() as db:
        authed = require_superadmin(request, db)
    return authed


@router.get("/tenants")
def list_tenants(_authed: Any = Depends(_superadmin_guard)) -> dict[str, Any]:
    """Every tenant with call counts and billed minutes. No PII: ids and totals."""

    with session_scope() as db:
        tenants = db.execute(select(Tenant)).scalars().all()
        calls = db.execute(select(Call)).scalars().all()

    minutes_by_tenant: dict[str, int] = {}
    calls_by_tenant: dict[str, int] = {}
    for call in calls:
        minutes = billed_minutes_for(
            call.duration_sec or 0,
            started_at=call.started_at,
            ended_at=call.ended_at,
        )
        minutes_by_tenant[call.tenant_id] = minutes_by_tenant.get(call.tenant_id, 0) + minutes
        calls_by_tenant[call.tenant_id] = calls_by_tenant.get(call.tenant_id, 0) + 1

    rows = [
        {
            "tenant_id": tenant.id,
            "name": tenant.name,
            "active": bool(tenant.active),
            "plan": getattr(tenant, "plan", None),
            "subscription_status": getattr(tenant, "subscription_status", None) or "trialing",
            "failed_payment_count": getattr(tenant, "failed_payment_count", None) or 0,
            "current_period_end": (
                tenant.current_period_end.isoformat() if getattr(tenant, "current_period_end", None) else None
            ),
            "call_count": calls_by_tenant.get(tenant.id, 0),
            "minutes_used": minutes_by_tenant.get(tenant.id, 0),
        }
        for tenant in tenants
    ]
    rows.sort(key=lambda row: row["minutes_used"], reverse=True)

    return {
        "tenant_count": len(rows),
        "total_calls": sum(calls_by_tenant.values()),
        "total_minutes": sum(minutes_by_tenant.values()),
        "tenants": rows,
    }
