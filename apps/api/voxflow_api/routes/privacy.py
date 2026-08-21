"""Tenant privacy lifecycle APIs with no automated export, deletion, or reset.

These routes expose aggregate evidence and a redacted review ledger only. Any
actual data disclosure, deletion, or demo reset remains blocked pending a
separate human-authorized procedure.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..auth import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER, require_tenant_role
from ..config import get_settings
from ..db import PrivacyRequest, Tenant, get_session
from ..privacy import (
    create_privacy_request,
    demo_reset_preview,
    get_or_create_policy,
    privacy_policy_payload,
    request_payload,
    retention_preview,
    review_privacy_request,
)


router = APIRouter(prefix="/api/privacy", tags=["privacy"])


class PrivacyPolicyIn(BaseModel):
    call_transcript_retention_days: int = Field(30, ge=0, le=3650)
    communication_retention_days: int = Field(30, ge=0, le=3650)
    recording_retention_days: int = Field(0, ge=0, le=3650)


class PrivacyRequestIn(BaseModel):
    request_type: Literal["access_export", "deletion"]
    subject_reference: str = Field(..., min_length=3, max_length=320)

    @field_validator("subject_reference")
    @classmethod
    def non_blank_subject_reference(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("subject_reference is required")
        return normalized


class PrivacyReviewIn(BaseModel):
    status: Literal["human_verification_required", "approved_for_manual_export", "blocked", "cancelled"]
    review_note: str = Field("", max_length=512)


def _require_tenant(db: Session, tenant_id: str) -> None:
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(status_code=404, detail="tenant_not_found")


def _read_access(request: Request, db: Session, tenant_id: str, *, allow_demo: bool = True) -> None:
    _require_tenant(db, tenant_id)
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
        allow_demo=allow_demo,
    )


def _owner_access(request: Request, db: Session, tenant_id: str) -> str:
    _require_tenant(db, tenant_id)
    actor = require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
    return actor.user_id


@router.get("/{tenant_id}/overview")
def get_privacy_overview(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Return redacted retention and workflow evidence; it changes no data."""

    _read_access(request, db, tenant_id)
    return retention_preview(db, tenant_id)


@router.get("/{tenant_id}/policy")
def get_privacy_policy(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Return retention settings without exposing customer records."""

    _read_access(request, db, tenant_id)
    return privacy_policy_payload(get_or_create_policy(db, tenant_id))


@router.put("/{tenant_id}/policy")
def update_privacy_policy(
    tenant_id: str,
    payload: PrivacyPolicyIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Update an owner-controlled retention policy; no purge is scheduled."""

    actor_id = _owner_access(request, db, tenant_id)
    policy = get_or_create_policy(db, tenant_id)
    policy.call_transcript_retention_days = payload.call_transcript_retention_days
    policy.communication_retention_days = payload.communication_retention_days
    policy.recording_retention_days = payload.recording_retention_days
    policy.updated_by = actor_id
    db.commit()
    db.refresh(policy)
    return {
        "ok": True,
        "policy": privacy_policy_payload(policy),
        "execution": "policy_only_no_purge_enqueued",
    }


@router.post("/{tenant_id}/requests")
def create_request(
    tenant_id: str,
    payload: PrivacyRequestIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Record a redacted access-export or deletion request for human review."""

    actor_id = _owner_access(request, db, tenant_id)
    request_row = create_privacy_request(
        db,
        tenant_id=tenant_id,
        request_type=payload.request_type,
        subject_reference=payload.subject_reference,
        requested_by=actor_id,
    )
    db.commit()
    return {
        "ok": True,
        "request": request_payload(request_row),
        "execution": "request_recorded_no_export_or_deletion_performed",
    }


@router.get("/{tenant_id}/requests")
def list_requests(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """List redacted request lifecycle evidence for owners and operators only."""

    _require_tenant(db, tenant_id)
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR},
        allow_demo=False,
    )
    requests = (
        db.query(PrivacyRequest)
        .filter(PrivacyRequest.tenant_id == tenant_id)
        .order_by(PrivacyRequest.created_at.desc())
        .all()
    )
    return {"tenant_id": tenant_id, "requests": [request_payload(row) for row in requests]}


@router.post("/{tenant_id}/requests/{privacy_request_id}/review")
def review_request(
    tenant_id: str,
    privacy_request_id: str,
    payload: PrivacyReviewIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Record a review state but never execute an export, deletion, or reset."""

    actor_id = _owner_access(request, db, tenant_id)
    request_row = (
        db.query(PrivacyRequest)
        .filter(PrivacyRequest.id == privacy_request_id, PrivacyRequest.tenant_id == tenant_id)
        .one_or_none()
    )
    if request_row is None:
        raise HTTPException(status_code=404, detail="privacy_request_not_found")
    reviewed = review_privacy_request(
        request_row,
        reviewed_by=actor_id,
        status=payload.status,
        review_note=payload.review_note,
    )
    db.commit()
    return {
        "ok": True,
        "request": request_payload(reviewed),
        "execution": "review_recorded_no_export_or_deletion_performed",
    }


@router.get("/{tenant_id}/demo-reset-preview")
def get_demo_reset_preview(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Return fixed safety gates for a potential sanitized demo reset only."""

    _read_access(request, db, tenant_id)
    return demo_reset_preview(tenant_id)


@router.post("/{tenant_id}/demo-reset-requests")
def create_demo_reset_request(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Record a blocked reset request for the configured demo tenant only."""

    actor_id = _owner_access(request, db, tenant_id)
    if tenant_id != get_settings().demo_tenant_id:
        raise HTTPException(status_code=409, detail="sanitized_demo_reset_limited_to_fixed_demo_tenant")
    request_row = create_privacy_request(
        db,
        tenant_id=tenant_id,
        request_type="demo_reset",
        subject_reference="",
        requested_by=actor_id,
    )
    db.commit()
    return {
        "ok": True,
        "request": request_payload(request_row),
        "execution": "blocked_request_only_no_reset_performed",
    }
