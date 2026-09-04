"""REST API endpoints for closed-loop escalation management, assignment, and resolution."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, Request, status

from ..auth import (
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    require_tenant_role,
)
from ..db import Call, session_scope
from ..routes.data import _call_out
from ..schemas import CallOut
from ..services.escalation_service import (
    VALID_PRIORITIES,
    VALID_RESOLUTION_CATEGORIES,
    assign_escalation,
    get_escalation_kpis,
    list_escalations,
    resolve_escalation,
)

router = APIRouter(prefix="/api/tenants/{tenant_id}/escalations", tags=["escalations"])


class EscalationMetricsOut(BaseModel):
    tenant_id: str
    total_escalations: int
    open_count: int
    pending_count: int
    in_progress_count: int
    resolved_count: int
    dismissed_count: int
    breached_count: int
    sla_compliance_rate: float
    avg_resolution_min: float


class EscalationsListOut(BaseModel):
    items: list[CallOut]
    total: int
    limit: int
    offset: int


class AssignEscalationIn(BaseModel):
    assigned_to_user_id: str | None = Field(default=None, description="Target member user ID or email, or null to unassign")


class ResolveEscalationIn(BaseModel):
    status: str = Field(default="resolved", description="Target status: 'resolved' or 'dismissed'")
    resolution_category: str = Field(default="callback_completed", description="Standard resolution category code")
    staff_resolution: str = Field(default="", description="Operator explanation and closing notes")


@router.get("", response_model=EscalationsListOut)
def list_tenant_escalation_queue(
    request: Request,
    tenant_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    breached_only: bool = Query(default=False),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List paginated escalations for a tenant with status, priority, search, and SLA breach filters."""
    if priority and priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid_priority: must be one of {sorted(VALID_PRIORITIES)}",
        )

    with session_scope() as db:
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        items, total = list_escalations(
            db=db,
            tenant_id=tenant_id,
            status=status_filter,
            priority=priority,
            breached_only=breached_only,
            search=search,
            limit=limit,
            offset=offset,
        )
        return {
            "items": [_call_out(c) for c in items],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.get("/metrics", response_model=EscalationMetricsOut)
def get_tenant_escalation_metrics(
    request: Request,
    tenant_id: str,
) -> dict[str, Any]:
    """Retrieve real-time SLA metrics, open ticket counts, and resolution compliance rates."""
    with session_scope() as db:
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        return get_escalation_kpis(db=db, tenant_id=tenant_id)


@router.get("/{call_id}", response_model=CallOut)
def get_tenant_escalation_detail(
    request: Request,
    tenant_id: str,
    call_id: str,
) -> dict[str, Any]:
    """Retrieve full detail for a single escalated call including transcript and actions."""
    with session_scope() as db:
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        c = db.get(Call, call_id)
        if not c or c.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="call_not_found")
        return _call_out(c)


@router.patch("/{call_id}/assign", response_model=CallOut)
def assign_tenant_escalation(
    request: Request,
    tenant_id: str,
    call_id: str,
    payload: AssignEscalationIn,
) -> dict[str, Any]:
    """Assign or claim an escalation ticket."""
    with session_scope() as db:
        actor = require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR},
            allow_demo=True,
        )
        if actor.is_demo and request.headers.get("X-VoxFlow-Demo-Write", "").lower() != "allowed":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="demo_access_read_only")

        try:
            call = assign_escalation(
                db=db,
                tenant_id=tenant_id,
                call_id=call_id,
                assigned_to_user_id=payload.assigned_to_user_id,
                actor_user_id=actor.user_id or "operator",
            )
            return _call_out(call)
        except ValueError as exc:
            if "call_not_found" in str(exc):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="call_not_found")
            if "assignee_not_active_member" in str(exc):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="assignee_not_active_member",
                )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{call_id}/resolve", response_model=CallOut)
def resolve_tenant_escalation(
    request: Request,
    tenant_id: str,
    call_id: str,
    payload: ResolveEscalationIn,
) -> dict[str, Any]:
    """Resolve or dismiss an escalation ticket with category and closing notes."""
    if payload.status not in ("resolved", "dismissed"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid_status: must be 'resolved' or 'dismissed', got '{payload.status}'",
        )

    if payload.resolution_category and payload.resolution_category not in VALID_RESOLUTION_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid_resolution_category: must be one of {sorted(VALID_RESOLUTION_CATEGORIES)}",
        )

    with session_scope() as db:
        actor = require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR},
            allow_demo=True,
        )
        if actor.is_demo and request.headers.get("X-VoxFlow-Demo-Write", "").lower() != "allowed":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="demo_access_read_only")

        try:
            call = resolve_escalation(
                db=db,
                tenant_id=tenant_id,
                call_id=call_id,
                status=payload.status,
                resolution_category=payload.resolution_category,
                staff_resolution=payload.staff_resolution,
                actor_user_id=actor.user_id or "operator",
            )
            return _call_out(call)
        except ValueError as exc:
            if "call_not_found" in str(exc):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="call_not_found")
            if "escalation_already_closed" in str(exc):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="escalation_already_closed")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
