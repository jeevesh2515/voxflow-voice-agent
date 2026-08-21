"""Administrative tenant-management routes with application-owned authorization."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..auth import (
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    normalized_email_hash,
    require_platform_admin,
    require_tenant_role,
)
from ..db import Call, Tenant, TenantMember, TenantPhoneNumber, session_scope
from ..jobs.side_effects import EMAIL_SUMMARIZATION_SCAN, enqueue_side_effect
from ..logging import get_logger


log = get_logger(__name__)
router = APIRouter()


class TenantCreateIn(BaseModel):
    id: str = Field(..., description="Unique slug for tenant, e.g. acme_corp")
    name: str = Field(..., description="Company display name")
    logo_url: str | None = None
    agent_name: str = "Vaani"
    system_prompt_override: str | None = None
    welcome_message: str | None = None
    default_language: str = "hi"
    webhook_url: str | None = None
    webhook_secret: str | None = None
    plan: str = "pro"


class TenantUpdateIn(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    agent_name: str | None = None
    system_prompt_override: str | None = None
    welcome_message: str | None = None
    default_language: str | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None
    plan: str | None = None
    active: int | None = None


class PhoneNumberMapIn(BaseModel):
    phone_number: str = Field(..., description="E.164 phone number, e.g. +14155550199")
    label: str = ""


def _tenant_summary(tenant: Tenant) -> dict[str, object]:
    return {
        "id": tenant.id,
        "name": tenant.name,
        "agent_name": tenant.agent_name,
        "default_language": tenant.default_language,
        "plan": tenant.plan,
        "total_minutes_used": tenant.total_minutes_used,
        "active": tenant.active,
        "created_at": tenant.created_at.isoformat(),
    }


# ---------- Tenant Endpoints ----------


@router.post("/tenants")
def create_tenant(payload: TenantCreateIn, request: Request) -> dict[str, Any]:
    """Create a tenant from the explicit platform-admin control plane only."""

    actor = require_platform_admin(request)
    with session_scope() as db:
        existing = db.get(Tenant, payload.id)
        if existing:
            raise HTTPException(status_code=409, detail="tenant_already_exists")
        tenant = Tenant(
            id=payload.id,
            name=payload.name,
            logo_url=payload.logo_url,
            agent_name=payload.agent_name,
            system_prompt_override=payload.system_prompt_override,
            welcome_message=payload.welcome_message,
            default_language=payload.default_language,
            webhook_url=payload.webhook_url,
            webhook_secret=payload.webhook_secret,
            plan=payload.plan,
        )
        db.add(tenant)
        db.flush()
        db.add(
            TenantMember(
                id=f"tm-{uuid.uuid4().hex[:20]}",
                tenant_id=tenant.id,
                user_id=actor.user_id,
                subject_email_hash=normalized_email_hash(actor.email, fallback_subject=actor.user_id),
                role=ROLE_OWNER,
                status="active",
                invited_by="platform_admin_bootstrap",
                activated_at=datetime.now(timezone.utc),
            )
        )
        log.info("admin.tenant_created", tenant_id=tenant.id, name=tenant.name, plan=tenant.plan)
        return {
            "ok": True,
            "tenant_id": tenant.id,
            "name": tenant.name,
            "agent_name": tenant.agent_name,
            "plan": tenant.plan,
            "owner_membership_created": True,
        }


@router.get("/tenants")
def list_all_tenants(request: Request) -> list[dict[str, Any]]:
    """List all client tenants for an explicit platform administrator only."""

    require_platform_admin(request)
    with session_scope() as db:
        rows = db.execute(select(Tenant).order_by(Tenant.created_at.desc())).scalars().all()
        return [_tenant_summary(tenant) for tenant in rows]


@router.get("/tenants/{tenant_id}")
def get_tenant_details(tenant_id: str, request: Request) -> dict[str, Any]:
    """Return tenant configuration to an authorized active member only."""

    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        return {
            "id": tenant.id,
            "name": tenant.name,
            "logo_url": tenant.logo_url,
            "agent_name": tenant.agent_name,
            "system_prompt_override": tenant.system_prompt_override,
            "welcome_message": tenant.welcome_message,
            "default_language": tenant.default_language,
            "webhook_configured": bool(tenant.webhook_url and tenant.webhook_secret),
            "plan": tenant.plan,
            "total_minutes_used": tenant.total_minutes_used,
            "active": tenant.active,
            "created_at": tenant.created_at.isoformat(),
        }


@router.patch("/tenants/{tenant_id}")
def update_tenant(tenant_id: str, payload: TenantUpdateIn, request: Request) -> dict[str, Any]:
    """Update tenant configuration as an owner; demo and operators cannot mutate it."""

    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(tenant, key, value)
        log.info("admin.tenant_updated", tenant_id=tenant_id)
        return {"ok": True, "tenant_id": tenant.id, "name": tenant.name, "plan": tenant.plan}


# ---------- Phone Mapping ----------


@router.post("/tenants/{tenant_id}/phone-numbers")
def map_phone_number_to_tenant(
    tenant_id: str,
    payload: PhoneNumberMapIn,
    request: Request,
) -> dict[str, Any]:
    """Assign an inbound number only as an owner-controlled configuration change."""

    clean_phone = payload.phone_number.strip().replace(" ", "")
    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
        existing = db.get(TenantPhoneNumber, clean_phone)
        if existing:
            existing.tenant_id = tenant_id
            existing.label = payload.label or existing.label
        else:
            db.add(
                TenantPhoneNumber(
                    phone_number=clean_phone,
                    tenant_id=tenant_id,
                    label=payload.label or f"{tenant.name} Support Line",
                )
            )
        log.info("admin.phone_mapped", tenant_id=tenant_id)
        return {"ok": True, "phone_number": clean_phone, "tenant_id": tenant_id}


# ---------- Usage & Billing Stats ----------


@router.get("/tenants/{tenant_id}/usage")
def get_tenant_usage_stats(tenant_id: str, request: Request) -> dict[str, Any]:
    """Return aggregate usage to an authorized active member only."""

    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        calls = db.execute(select(Call).where(Call.tenant_id == tenant_id)).scalars().all()
        total_calls = len(calls)
        total_seconds = sum(call.duration_sec for call in calls)
        total_minutes = round(total_seconds / 60.0, 2)
        resolved_calls = sum(1 for call in calls if call.resolution_status == "resolved")
        escalated_calls = sum(1 for call in calls if call.escalated == 1)
        rate_per_min = 0.15
        billable_amount_usd = round(total_minutes * rate_per_min, 2)
        return {
            "tenant_id": tenant_id,
            "company_name": tenant.name,
            "plan": tenant.plan,
            "total_calls": total_calls,
            "total_duration_sec": total_seconds,
            "total_minutes": total_minutes,
            "resolved_calls": resolved_calls,
            "escalated_calls": escalated_calls,
            "resolution_rate": round(resolved_calls / total_calls * 100, 1) if total_calls else 100.0,
            "rate_per_minute_usd": rate_per_min,
            "estimated_bill_usd": billable_amount_usd,
        }


# ---------- Email Summarizer Agent Endpoints ----------


@router.post("/email-summarizer/run")
def run_email_summarizer_now(
    request: Request,
    tenant_id: str = Query("varun", description="Tenant ID to summarize emails for"),
    limit: int = Query(15, ge=1, le=50, description="Max emails to process"),
) -> dict[str, Any]:
    """Record a durable email scan request as a tenant owner; never run it inline."""

    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
        result = enqueue_side_effect(
            db,
            tenant_id=tenant_id,
            effect_type=EMAIL_SUMMARIZATION_SCAN,
            aggregate_type="email_scan",
            aggregate_id=str(limit),
            idempotency_key=f"email-scan:{tenant_id}:{limit}",
            max_attempts=3,
            trace_id=f"email-manual:{tenant_id}",
        )
    return {
        "ok": True,
        "queued": True,
        "tenant_id": tenant_id,
        "limit": limit,
        "job_id": result.job_id,
        "outbox_id": result.outbox_id,
        "created": result.created,
    }


@router.get("/email-summarizer/status")
def get_email_summarizer_status(
    request: Request,
    tenant_id: str = Query("varun", description="Tenant ID"),
) -> dict[str, Any]:
    """Return email summarizer state to a tenant member without credentials."""

    import json

    from ..config import get_settings
    from ..db import AgentState

    with session_scope() as db:
        if db.get(Tenant, tenant_id) is None:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        state_key = f"email_summarizer_last_run_{tenant_id}"
        state = db.execute(select(AgentState).where(AgentState.key == state_key)).scalars().first()
        last_run_data = json.loads(state.value_json) if state and state.value_json else {}
        ids_key = f"processed_email_ids_{tenant_id}"
        ids_state = db.execute(select(AgentState).where(AgentState.key == ids_key)).scalars().first()
        processed_count = len(json.loads(ids_state.value_json)) if ids_state and ids_state.value_json else 0
        settings = get_settings()
        return {
            "enabled": settings.email_summarizer_enabled,
            "interval_seconds": settings.email_summarizer_interval_seconds,
            "gmail_user_email": "configured" if settings.gmail_user_email else "not_configured",
            "sheets_enabled": settings.sheets_enabled,
            "sheets_id_configured": bool(settings.google_sheet_id),
            "email_tab": settings.google_sheet_email_tab,
            "last_run": last_run_data.get("last_run"),
            "total_processed_unique_emails": processed_count,
        }
