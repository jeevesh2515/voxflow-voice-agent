"""Tenant-scoped campaign policy controls and recipient preference APIs for Day 30."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER, require_tenant_role
from ..db import RecipientCampaignPreference, Tenant, TenantCampaignPolicy, get_session

router = APIRouter(prefix="/api/campaign-policies", tags=["campaign-policies"])

_CLOCK_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class CampaignPolicyIn(BaseModel):
    timezone_name: str = "Asia/Kolkata"
    calling_window_start: str = "09:00"
    calling_window_end: str = "20:00"
    daily_call_limit: int = Field(100, ge=1, le=100_000)
    max_in_flight: int = Field(1, ge=1, le=1_000)
    enabled: bool = True


class RecipientPreferenceIn(BaseModel):
    consent_status: str = Field("granted", pattern="^(granted|withdrawn|unknown)$")
    consent_purpose: str = Field("outbound_campaign", min_length=1, max_length=64)
    opted_out: bool = False
    source: str = Field("operator", min_length=1, max_length=128)


def _require_tenant(request: Request, db: Session, tenant_id: str, *, write: bool = False, allow_demo: bool = True) -> None:
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR} if write else {ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
        allow_demo=allow_demo and not write,
    )


def _validate_policy(value: CampaignPolicyIn) -> None:
    if not _CLOCK_RE.fullmatch(value.calling_window_start) or not _CLOCK_RE.fullmatch(value.calling_window_end):
        raise HTTPException(status_code=422, detail="Calling windows must use 24-hour HH:MM format")
    if value.calling_window_start == value.calling_window_end:
        raise HTTPException(status_code=422, detail="Calling window start and end must differ")
    try:
        ZoneInfo(value.timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=422, detail="timezone_name must be a valid IANA timezone") from exc


def _policy_payload(policy: TenantCampaignPolicy | None, tenant_id: str) -> dict[str, object]:
    if policy is None:
        return {"tenant_id": tenant_id, "configured": False}
    return {
        "tenant_id": tenant_id,
        "configured": True,
        "timezone_name": policy.timezone_name,
        "calling_window_start": policy.calling_window_start,
        "calling_window_end": policy.calling_window_end,
        "daily_call_limit": policy.daily_call_limit,
        "max_in_flight": policy.max_in_flight,
        "enabled": bool(policy.enabled),
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


@router.get("/{tenant_id}")
def get_campaign_policy(tenant_id: str, request: Request, db: Session = Depends(get_session)) -> dict[str, object]:
    """Read one tenant's policy configuration without exposing recipient data."""

    _require_tenant(request, db, tenant_id)
    return _policy_payload(db.get(TenantCampaignPolicy, tenant_id), tenant_id)


@router.put("/{tenant_id}")
def upsert_campaign_policy(
    tenant_id: str,
    payload: CampaignPolicyIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Create or replace an explicit policy gate for a single tenant."""

    _require_tenant(request, db, tenant_id, write=True)
    _validate_policy(payload)
    policy = db.get(TenantCampaignPolicy, tenant_id)
    if policy is None:
        policy = TenantCampaignPolicy(tenant_id=tenant_id)
        db.add(policy)
    policy.timezone_name = payload.timezone_name
    policy.calling_window_start = payload.calling_window_start
    policy.calling_window_end = payload.calling_window_end
    policy.daily_call_limit = payload.daily_call_limit
    policy.max_in_flight = payload.max_in_flight
    policy.enabled = int(payload.enabled)
    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return _policy_payload(policy, tenant_id)


@router.put("/{tenant_id}/recipients/{recipient_phone}")
def upsert_recipient_preference(
    tenant_id: str,
    recipient_phone: str,
    payload: RecipientPreferenceIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Persist tenant-owned outbound-call consent and opt-out state for one recipient."""

    _require_tenant(request, db, tenant_id, write=True, allow_demo=False)
    if not recipient_phone.startswith("+"):
        raise HTTPException(status_code=422, detail="recipient_phone must use E.164 format")
    preference = (
        db.query(RecipientCampaignPreference)
        .filter(
            RecipientCampaignPreference.tenant_id == tenant_id,
            RecipientCampaignPreference.recipient_phone == recipient_phone,
        )
        .one_or_none()
    )
    if preference is None:
        preference = RecipientCampaignPreference(
            id=f"rcp-{uuid.uuid4().hex[:20]}",
            tenant_id=tenant_id,
            recipient_phone=recipient_phone,
        )
        db.add(preference)
    preference.consent_status = payload.consent_status
    preference.consent_purpose = payload.consent_purpose
    preference.opted_out = int(payload.opted_out)
    preference.source = payload.source
    preference.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "tenant_id": tenant_id,
        "recipient_phone": recipient_phone,
        "consent_status": preference.consent_status,
        "consent_purpose": preference.consent_purpose,
        "opted_out": bool(preference.opted_out),
        "source": preference.source,
        "updated_at": preference.updated_at.isoformat() if preference.updated_at else None,
    }


@router.get("/{tenant_id}/recipients/{recipient_phone}")
def get_recipient_preference(
    tenant_id: str,
    recipient_phone: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object]:
    """Read a single tenant-owned recipient preference record."""

    _require_tenant(request, db, tenant_id, allow_demo=False)
    preference = (
        db.query(RecipientCampaignPreference)
        .filter(
            RecipientCampaignPreference.tenant_id == tenant_id,
            RecipientCampaignPreference.recipient_phone == recipient_phone,
        )
        .one_or_none()
    )
    if preference is None:
        raise HTTPException(status_code=404, detail="Recipient preference not found")
    return {
        "tenant_id": tenant_id,
        "recipient_phone": recipient_phone,
        "consent_status": preference.consent_status,
        "consent_purpose": preference.consent_purpose,
        "opted_out": bool(preference.opted_out),
        "source": preference.source,
        "updated_at": preference.updated_at.isoformat() if preference.updated_at else None,
    }
