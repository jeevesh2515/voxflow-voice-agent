"""Read-only Day 36 pilot-operations reliability APIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER, require_tenant_role
from ..db import Tenant, get_session
from ..pilot_operations import hold_point_scorecard, operational_preflight


router = APIRouter(prefix="/api/pilot-operations", tags=["pilot-operations"])


def _require_tenant(request: Request, db: Session, tenant_id: str) -> None:
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
        allow_demo=True,
    )


@router.get("/{tenant_id}/preflight")
def get_pilot_preflight(tenant_id: str, request: Request, db: Session = Depends(get_session)) -> dict[str, object]:
    """Return redacted Day 36 queue, callback, and readiness evidence.

    This endpoint cannot record a decision, approve a tenant, pause a worker,
    start a worker, create a campaign, or contact an external service.
    """

    _require_tenant(request, db, tenant_id)
    return operational_preflight(db, tenant_id=tenant_id)


@router.get("/{tenant_id}/hold-point")
def get_pilot_hold_point(tenant_id: str, request: Request, db: Session = Depends(get_session)) -> dict[str, object]:
    """Return the current no-auto-expansion hold-point state for one tenant."""

    _require_tenant(request, db, tenant_id)
    return hold_point_scorecard(db, tenant_id=tenant_id)
