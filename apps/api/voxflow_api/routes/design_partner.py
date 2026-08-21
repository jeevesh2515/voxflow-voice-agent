"""Read-only design-partner and controlled-pilot readiness API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER, require_tenant_role
from ..db import Tenant, get_session
from ..design_partner import design_partner_readiness


router = APIRouter(prefix="/api/design-partner", tags=["design-partner"])


@router.get("/{tenant_id}/readiness")
def get_design_partner_readiness(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Return a non-executable, redacted readiness scorecard for one tenant."""

    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(status_code=404, detail="tenant_not_found")
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
        allow_demo=True,
    )
    return design_partner_readiness(db, tenant_id)
