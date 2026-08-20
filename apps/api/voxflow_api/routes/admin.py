"""Admin & SaaS Tenant Management API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..db import Call, Tenant, TenantPhoneNumber, session_scope
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


# ---------- Tenant Endpoints ----------


@router.post("/tenants")
def create_tenant(payload: TenantCreateIn) -> dict[str, Any]:
    """Create a new client tenant in the SaaS platform."""
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
        log.info("admin.tenant_created", tenant_id=tenant.id, name=tenant.name, plan=tenant.plan)
        return {
            "ok": True,
            "tenant_id": tenant.id,
            "name": tenant.name,
            "agent_name": tenant.agent_name,
            "plan": tenant.plan,
        }


@router.get("/tenants")
def list_all_tenants() -> list[dict[str, Any]]:
    """List all client tenants registered in the platform."""
    with session_scope() as db:
        rows = db.execute(select(Tenant).order_by(Tenant.created_at.desc())).scalars().all()
        return [
            {
                "id": t.id,
                "name": t.name,
                "agent_name": t.agent_name,
                "default_language": t.default_language,
                "plan": t.plan,
                "total_minutes_used": t.total_minutes_used,
                "active": t.active,
                "created_at": t.created_at.isoformat(),
            }
            for t in rows
        ]


@router.get("/tenants/{tenant_id}")
def get_tenant_details(tenant_id: str) -> dict[str, Any]:
    """Get full details and configuration for a specific tenant."""
    with session_scope() as db:
        t = db.get(Tenant, tenant_id)
        if not t:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        return {
            "id": t.id,
            "name": t.name,
            "logo_url": t.logo_url,
            "agent_name": t.agent_name,
            "system_prompt_override": t.system_prompt_override,
            "welcome_message": t.welcome_message,
            "default_language": t.default_language,
            "webhook_url": t.webhook_url,
            "plan": t.plan,
            "total_minutes_used": t.total_minutes_used,
            "active": t.active,
            "created_at": t.created_at.isoformat(),
        }


@router.patch("/tenants/{tenant_id}")
def update_tenant(tenant_id: str, payload: TenantUpdateIn) -> dict[str, Any]:
    """Update tenant persona, custom prompt override, webhook, or subscription plan."""
    with session_scope() as db:
        t = db.get(Tenant, tenant_id)
        if not t:
            raise HTTPException(status_code=404, detail="tenant_not_found")

        for key, val in payload.model_dump(exclude_unset=True).items():
            setattr(t, key, val)

        db.flush()
        log.info("admin.tenant_updated", tenant_id=tenant_id)
        return {"ok": True, "tenant_id": t.id, "name": t.name, "plan": t.plan}


# ---------- Phone Mapping ----------


@router.post("/tenants/{tenant_id}/phone-numbers")
def map_phone_number_to_tenant(tenant_id: str, payload: PhoneNumberMapIn) -> dict[str, Any]:
    """Assign an inbound telephone number to a tenant."""
    clean_phone = payload.phone_number.strip().replace(" ", "")
    with session_scope() as db:
        t = db.get(Tenant, tenant_id)
        if not t:
            raise HTTPException(status_code=404, detail="tenant_not_found")

        existing = db.get(TenantPhoneNumber, clean_phone)
        if existing:
            existing.tenant_id = tenant_id
            existing.label = payload.label or existing.label
        else:
            tpn = TenantPhoneNumber(
                phone_number=clean_phone,
                tenant_id=tenant_id,
                label=payload.label or f"{t.name} Support Line",
            )
            db.add(tpn)

        db.flush()
        log.info("admin.phone_mapped", phone=clean_phone, tenant_id=tenant_id)
        return {"ok": True, "phone_number": clean_phone, "tenant_id": tenant_id}


# ---------- Usage & Billing Stats ----------


@router.get("/tenants/{tenant_id}/usage")
def get_tenant_usage_stats(tenant_id: str) -> dict[str, Any]:
    """Get exact call duration, turns, resolution rates, and billing estimates for a tenant."""
    with session_scope() as db:
        t = db.get(Tenant, tenant_id)
        if not t:
            raise HTTPException(status_code=404, detail="tenant_not_found")

        calls = db.execute(select(Call).where(Call.tenant_id == tenant_id)).scalars().all()
        total_calls = len(calls)
        total_seconds = sum(c.duration_sec for c in calls)
        total_minutes = round(total_seconds / 60.0, 2)
        resolved_calls = sum(1 for c in calls if c.resolution_status == "resolved")
        escalated_calls = sum(1 for c in calls if c.escalated == 1)

        rate_per_min = 0.15  # standard $0.15/min SaaS pricing
        billable_amount_usd = round(total_minutes * rate_per_min, 2)

        return {
            "tenant_id": tenant_id,
            "company_name": t.name,
            "plan": t.plan,
            "total_calls": total_calls,
            "total_duration_sec": total_seconds,
            "total_minutes": total_minutes,
            "resolved_calls": resolved_calls,
            "escalated_calls": escalated_calls,
            "resolution_rate": round(resolved_calls / total_calls * 100, 1) if total_calls > 0 else 100.0,
            "rate_per_minute_usd": rate_per_min,
            "estimated_bill_usd": billable_amount_usd,
        }


# ---------- Email Summarizer Agent Endpoints ----------


@router.post("/email-summarizer/run")
def run_email_summarizer_now(
    tenant_id: str = Query("varun", description="Tenant ID to summarize emails for"),
    limit: int = Query(15, ge=1, le=50, description="Max emails to process"),
) -> dict[str, Any]:
    """Record a durable email scan request without fetching email inline."""

    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        result = enqueue_side_effect(
            db,
            tenant_id=tenant_id,
            effect_type=EMAIL_SUMMARIZATION_SCAN,
            aggregate_type="email_scan",
            aggregate_id=str(limit),
            # A manual request is intentionally idempotent only within a bounded
            # minute bucket. Operators may request another audited scan later.
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
    tenant_id: str = Query("varun", description="Tenant ID"),
) -> dict[str, Any]:
    """Get Email Summarizer operational status and last run metadata."""
    import json
    from ..config import get_settings
    from ..db import AgentState
    s = get_settings()
    state_key = f"email_summarizer_last_run_{tenant_id}"
    with session_scope() as db:
        state = db.execute(select(AgentState).where(AgentState.key == state_key)).scalars().first()
        last_run_data = json.loads(state.value_json) if state and state.value_json else {}

        ids_key = f"processed_email_ids_{tenant_id}"
        ids_state = db.execute(select(AgentState).where(AgentState.key == ids_key)).scalars().first()
        processed_count = len(json.loads(ids_state.value_json)) if ids_state and ids_state.value_json else 0

        return {
            "enabled": s.email_summarizer_enabled,
            "interval_seconds": s.email_summarizer_interval_seconds,
            "gmail_user_email": s.gmail_user_email or "Sample / Simulation Mode",
            "sheets_enabled": s.sheets_enabled,
            "sheets_id": s.google_sheet_id,
            "email_tab": s.google_sheet_email_tab,
            "last_run": last_run_data.get("last_run"),
            "total_processed_unique_emails": processed_count,
        }
