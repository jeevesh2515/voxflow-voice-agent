"""Read-only Day 35 controlled-pilot readiness APIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER, require_tenant_role
from ..db import Tenant, get_session
from ..pilot_readiness import pilot_scorecard, rollback_preview


router = APIRouter(prefix="/api/pilot-readiness", tags=["pilot-readiness"])


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


@router.get("/{tenant_id}")
def get_pilot_readiness(tenant_id: str, request: Request, db: Session = Depends(get_session)) -> dict[str, object]:
    """Return a tenant-safe scorecard and explicit blockers for pilot review.

    This endpoint cannot create a pilot, change an approval, enable a worker,
    enqueue a call, register a callback, or run a rollback. It only reports the
    current persisted evidence and the frozen denominator definitions.
    """

    _require_tenant(request, db, tenant_id)
    return pilot_scorecard(db, tenant_id=tenant_id)


@router.get("/{tenant_id}/rollback-preview")
def get_rollback_preview(tenant_id: str, request: Request, db: Session = Depends(get_session)) -> dict[str, object]:
    """Return the database-only rollback preconditions and scoped cancellation plan."""

    _require_tenant(request, db, tenant_id)
    return rollback_preview(db, tenant_id=tenant_id)
