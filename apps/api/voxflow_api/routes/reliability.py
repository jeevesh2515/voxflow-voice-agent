"""Read-only Day 37 reliability evidence APIs.

These endpoints deliberately do not expose a mutation or drill-run command. A
browser can inspect tenant-scoped SLOs, prior trusted drill receipts, and a
non-executable recovery preview only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..auth import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER, require_tenant_role
from ..db import Tenant, get_session
from ..reliability import list_drill_results, recovery_plan_preview, reliability_scorecard


router = APIRouter(prefix="/api/reliability", tags=["reliability"])


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


@router.get("/{tenant_id}/slos")
def get_reliability_slos(tenant_id: str, request: Request, db: Session = Depends(get_session)) -> dict[str, object]:
    """Return a redacted tenant SLO scorecard without changing any state."""

    _require_tenant(request, db, tenant_id)
    return reliability_scorecard(db, tenant_id=tenant_id)


@router.get("/{tenant_id}/drills")
def get_drill_results(
    tenant_id: str,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Return immutable database-only drill receipts; the endpoint cannot run a drill."""

    _require_tenant(request, db, tenant_id)
    return list_drill_results(db, tenant_id=tenant_id, limit=limit)


@router.get("/{tenant_id}/recovery-preview")
def get_recovery_preview(tenant_id: str, request: Request, db: Session = Depends(get_session)) -> dict[str, object]:
    """Return non-executable recovery guidance and no state-changing control."""

    _require_tenant(request, db, tenant_id)
    return recovery_plan_preview(db, tenant_id=tenant_id)
