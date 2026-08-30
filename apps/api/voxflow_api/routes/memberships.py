"""Tenant membership lifecycle APIs backed by the application authorization ledger.

Inviting records a pending membership only. This router neither sends an email
nor provisions a tenant, starts a worker, contacts a provider, or activates a
pilot. Invitation delivery remains an explicit human-owned design-partner step.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (
    ROLE_OPERATOR,
    ROLE_OWNER,
    active_membership,
    membership_summary,
    normalized_email_hash,
    require_authenticated_user,
    require_tenant_role,
)
from ..config import get_settings
from ..db import Tenant, TenantMember, get_session


router = APIRouter(prefix="/api/tenants", tags=["tenant-memberships"])


class MemberInviteIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    role: Literal["owner", "operator", "viewer"] = "viewer"
    user_id: str | None = Field(default=None, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("a valid email address is required")
        return normalized


class MemberAcceptIn(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=64)


def _require_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant_not_found")
    return tenant


def _membership_payload(member: TenantMember, tenant: Tenant | None = None) -> dict[str, object]:
    payload = membership_summary(member)
    if tenant is not None:
        payload["tenant"] = {
            "id": tenant.id,
            "name": tenant.name,
            "logo_url": tenant.logo_url,
            "agent_name": tenant.agent_name,
            "plan": tenant.plan,
        }
    return payload


@router.get("/memberships")
def list_my_memberships(request: Request, db: Session = Depends(get_session)) -> dict[str, object]:
    """List active, server-authorized workspaces for the current identity only."""

    auth = require_authenticated_user(request, allow_demo=True)
    if auth.is_demo:
        tenant = _require_tenant(db, get_settings().demo_tenant_id)
        return {
            "memberships": [
                {
                    "id": "demo-readonly-membership",
                    "tenant_id": tenant.id,
                    "user_id": auth.user_id,
                    "role": "viewer",
                    "status": "active",
                    "tenant": {
                        "id": tenant.id,
                        "name": tenant.name,
                        "logo_url": tenant.logo_url,
                        "agent_name": tenant.agent_name,
                        "plan": tenant.plan,
                    },
                }
            ],
            "demo_mode": True,
        }

    rows = db.execute(
        select(TenantMember, Tenant)
        .join(Tenant, Tenant.id == TenantMember.tenant_id)
        .where(TenantMember.user_id == auth.user_id, TenantMember.status == "active", Tenant.active == 1)
        .order_by(Tenant.name.asc())
    ).all()
    return {
        "memberships": [_membership_payload(member, tenant) for member, tenant in rows],
        "demo_mode": False,
    }


@router.post("/memberships/accept")
def accept_membership_invitation(
    payload: MemberAcceptIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Activate a pending invitation that matches the authenticated email hash."""

    auth = require_authenticated_user(request)
    _require_tenant(db, payload.tenant_id)
    email_hash = normalized_email_hash(auth.email, fallback_subject=auth.user_id)
    membership = (
        db.query(TenantMember)
        .filter(
            TenantMember.tenant_id == payload.tenant_id,
            TenantMember.subject_email_hash == email_hash,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="membership_invitation_not_found")
    if membership.status == "revoked":
        raise HTTPException(status_code=403, detail="membership_invitation_revoked")
    if membership.user_id not in (None, auth.user_id):
        raise HTTPException(status_code=409, detail="membership_identity_conflict")

    created = membership.status != "active"
    membership.user_id = auth.user_id
    membership.status = "active"
    membership.activated_at = membership.activated_at or datetime.now(timezone.utc)
    membership.revoked_at = None
    membership.revoked_by = None
    db.commit()
    return {"ok": True, "created": created, "membership": _membership_payload(membership)}


@router.get("/{tenant_id}/members")
def list_tenant_members(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """List redacted membership lifecycle records for an owner or operator."""

    _require_tenant(db, tenant_id)
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR},
    )
    rows = (
        db.query(TenantMember)
        .filter(TenantMember.tenant_id == tenant_id)
        .order_by(TenantMember.created_at.asc())
        .all()
    )
    return {"tenant_id": tenant_id, "members": [_membership_payload(member) for member in rows]}


@router.post("/{tenant_id}/members/invite")
def invite_tenant_member(
    tenant_id: str,
    payload: MemberInviteIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Create or refresh a pending membership invitation as a tenant owner.

    The route stores no raw email and sends no invitation itself. A design
    partner must deliver the invite through an approved human-owned channel.
    """

    _require_tenant(db, tenant_id)
    actor = require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
    email_hash = normalized_email_hash(payload.email)
    member = (
        db.query(TenantMember)
        .filter(TenantMember.tenant_id == tenant_id, TenantMember.subject_email_hash == email_hash)
        .first()
    )
    now = datetime.now(timezone.utc)
    created = member is None
    if member is None:
        member = TenantMember(
            id=f"tm-{uuid.uuid4().hex[:20]}",
            tenant_id=tenant_id,
            user_id=payload.user_id.strip() if payload.user_id else None,
            subject_email_hash=email_hash,
            role=payload.role,
            status="invited",
            invited_by=actor.user_id,
            created_at=now,
        )
        db.add(member)
    else:
        if member.status == "active" and member.user_id and payload.user_id not in (None, member.user_id):
            raise HTTPException(status_code=409, detail="active_membership_identity_conflict")
        member.role = payload.role
        member.status = "invited" if member.status != "active" else "active"
        member.user_id = member.user_id or (payload.user_id.strip() if payload.user_id else None)
        member.invited_by = actor.user_id
        member.revoked_at = None
        member.revoked_by = None
    db.commit()
    return {
        "ok": True,
        "created": created,
        "delivery": "manual_design_partner_invitation_required",
        "membership": _membership_payload(member),
    }


@router.delete("/{tenant_id}/members/{user_id}")
def revoke_tenant_member(
    tenant_id: str,
    user_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Revoke a member safely while protecting the last active owner."""

    _require_tenant(db, tenant_id)
    actor = require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
    if user_id == actor.user_id:
        raise HTTPException(status_code=409, detail="owner_cannot_revoke_self")
    member = active_membership(db, tenant_id=tenant_id, user_id=user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="active_membership_not_found")
    if member.role == ROLE_OWNER:
        owner_count = (
            db.query(TenantMember)
            .filter(
                TenantMember.tenant_id == tenant_id,
                TenantMember.role == ROLE_OWNER,
                TenantMember.status == "active",
            )
            .count()
        )
        if owner_count <= 1:
            raise HTTPException(status_code=409, detail="last_active_owner_cannot_be_revoked")

    member.status = "revoked"
    member.revoked_by = actor.user_id
    member.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "membership": _membership_payload(member)}


class MemberRoleUpdateIn(BaseModel):
    role: Literal["owner", "operator", "viewer"]


@router.patch("/{tenant_id}/members/{user_id}/role")
def update_member_role(
    tenant_id: str,
    user_id: str,
    payload: MemberRoleUpdateIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Update a member's role safely while protecting the last active owner."""

    _require_tenant(db, tenant_id)
    actor = require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
    member = active_membership(db, tenant_id=tenant_id, user_id=user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="active_membership_not_found")

    if member.role == ROLE_OWNER and payload.role != ROLE_OWNER:
        owner_count = (
            db.query(TenantMember)
            .filter(
                TenantMember.tenant_id == tenant_id,
                TenantMember.role == ROLE_OWNER,
                TenantMember.status == "active",
            )
            .count()
        )
        if owner_count <= 1:
            raise HTTPException(status_code=409, detail="last_active_owner_cannot_be_demoted")

    member.role = payload.role
    db.commit()
    return {"ok": True, "membership": _membership_payload(member)}

