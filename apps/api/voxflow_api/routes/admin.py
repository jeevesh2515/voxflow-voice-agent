"""Administrative tenant-management routes with application-owned authorization."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..agent.runner import clear_tenant_prompt_cache
from ..auth import (
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    normalized_email_hash,
    require_platform_admin,
    require_tenant_role,
)
from ..db import Call, Supplier, Tenant, TenantMember, TenantPhoneNumber, session_scope
from ..jobs.side_effects import EMAIL_SUMMARIZATION_SCAN, enqueue_side_effect
from ..logging import get_logger
from ..services.pin_security import hash_pin
from ..services.telephony_routing import normalize_e164


log = get_logger(__name__)
router = APIRouter()
tenant_settings_router = APIRouter(prefix="/api/tenants", tags=["tenant-telephony-settings"])


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


VALID_VOICE_PERSONAS = frozenset({"professional", "friendly", "concise", "assertive"})
VALID_ESCALATION_MODES = frozenset({"human_callback", "transfer", "voicemail"})
VALID_LANGUAGES = frozenset({"en", "hi"})


def _is_valid_time(val: str) -> bool:
    if not isinstance(val, str) or len(val) != 5 or val[2] != ":":
        return False
    hh, mm = val[:2], val[3:]
    if not (hh.isdigit() and mm.isdigit()):
        return False
    return 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59


class TenantAgentSettingsOut(BaseModel):
    tenant_id: str
    name: str
    agent_name: str
    voice_persona: str
    default_language: str
    welcome_message: str | None = None
    system_prompt_override: str | None = None
    business_hours_enabled: bool
    business_hours_start: str
    business_hours_end: str
    business_hours_timezone: str
    business_days: str
    out_of_hours_message: str | None = None
    fallback_escalation_mode: str
    fallback_phone: str | None = None
    fallback_email: str | None = None
    max_verification_failures: int


class TenantAgentSettingsUpdateIn(BaseModel):
    agent_name: str | None = None
    voice_persona: str | None = None
    default_language: str | None = None
    welcome_message: str | None = None
    system_prompt_override: str | None = None
    business_hours_enabled: bool | None = None
    business_hours_start: str | None = None
    business_hours_end: str | None = None
    business_hours_timezone: str | None = None
    business_days: str | None = None
    out_of_hours_message: str | None = None
    fallback_escalation_mode: str | None = None
    fallback_phone: str | None = None
    fallback_email: str | None = None
    max_verification_failures: int | None = None


class PhoneNumberMapIn(BaseModel):
    # Only "connect" is exposed for creation today: Amazon Connect is the only
    # provider with a wired inbound resolution route (routes/connect.py). The
    # database column still accepts "twilio"/"telnyx" for forward-compatible
    # storage, but the owner-facing API must not let a tenant create a mapping
    # that will never receive a call, so it is not offered here yet.
    phone_number: str = Field(..., description="E.164 phone number, e.g. +14155550199")
    label: str = ""
    provider: Literal["connect"] = "connect"
    verification_mode: Literal["standard", "enhanced"] = "standard"
    route_language: Literal["tenant_default", "en", "hi"] = "tenant_default"
    active: bool = True


class PhoneNumberUpdateIn(BaseModel):
    label: str | None = None
    provider: Literal["connect"] | None = None
    verification_mode: Literal["standard", "enhanced"] | None = None
    route_language: Literal["tenant_default", "en", "hi"] | None = None
    active: bool | None = None


class CallerPinSetIn(BaseModel):
    # Validation is intentionally performed in the route. Pydantic validation
    # errors include rejected input values, which would echo a raw PIN.
    pin: Any
    confirm_pin: Any = None


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


def _phone_number_summary(row: TenantPhoneNumber) -> dict[str, Any]:
    return {
        "phone_number": row.phone_number,
        "tenant_id": row.tenant_id,
        "label": row.label,
        "provider": row.provider,
        "verification_mode": row.verification_mode,
        "route_language": row.route_language,
        "active": bool(row.active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _masked_phone(phone_number: str) -> str:
    digits = "".join(character for character in phone_number if character.isdigit())
    if len(digits) < 4:
        return "••••"
    return f"+{'•' * max(0, len(digits) - 4)}{digits[-4:]}"


def _is_pin_locked(supplier: Supplier) -> bool:
    """Report persistent lockout state without exposing the PIN or hash.

    SQLite returns naive datetimes even for timezone-aware columns, so a
    direct comparison against an aware ``now`` must normalize first.
    """
    locked_until = supplier.pin_locked_until
    if locked_until is None:
        return False
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > datetime.now(timezone.utc)


@tenant_settings_router.get("/{tenant_id}/agent-settings", response_model=TenantAgentSettingsOut)
@router.get("/tenants/{tenant_id}/agent-settings", response_model=TenantAgentSettingsOut)
def get_tenant_agent_settings(tenant_id: str, request: Request) -> TenantAgentSettingsOut:
    """Return the tenant's persona, business hours, prompt templates, and fallback rules."""
    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        return TenantAgentSettingsOut(
            tenant_id=tenant.id,
            name=tenant.name,
            agent_name=tenant.agent_name or "Vaani",
            voice_persona=tenant.voice_persona or "professional",
            default_language=tenant.default_language or "en",
            welcome_message=tenant.welcome_message,
            system_prompt_override=tenant.system_prompt_override,
            business_hours_enabled=bool(tenant.business_hours_enabled),
            business_hours_start=tenant.business_hours_start or "09:00",
            business_hours_end=tenant.business_hours_end or "18:00",
            business_hours_timezone=tenant.business_hours_timezone or "Asia/Kolkata",
            business_days=tenant.business_days or "mon,tue,wed,thu,fri",
            out_of_hours_message=tenant.out_of_hours_message,
            fallback_escalation_mode=tenant.fallback_escalation_mode or "human_callback",
            fallback_phone=tenant.fallback_phone,
            fallback_email=tenant.fallback_email,
            max_verification_failures=tenant.max_verification_failures or 3,
        )


@tenant_settings_router.patch("/{tenant_id}/agent-settings", response_model=TenantAgentSettingsOut)
@router.patch("/tenants/{tenant_id}/agent-settings", response_model=TenantAgentSettingsOut)
def update_tenant_agent_settings(
    tenant_id: str,
    payload: TenantAgentSettingsUpdateIn,
    request: Request,
) -> TenantAgentSettingsOut:
    """Update tenant agent settings as an owner with server-authoritative validation."""
    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        actor = require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER},
            allow_demo=True,
        )

        if payload.agent_name is not None:
            cleaned = payload.agent_name.strip()
            if not cleaned:
                raise HTTPException(status_code=422, detail="agent_name_cannot_be_empty")
            tenant.agent_name = cleaned

        if payload.voice_persona is not None:
            if payload.voice_persona not in VALID_VOICE_PERSONAS:
                raise HTTPException(
                    status_code=422,
                    detail=f"invalid_voice_persona: must be one of {sorted(VALID_VOICE_PERSONAS)}",
                )
            tenant.voice_persona = payload.voice_persona

        if payload.default_language is not None:
            if payload.default_language not in VALID_LANGUAGES:
                raise HTTPException(
                    status_code=422,
                    detail=f"invalid_default_language: must be one of {sorted(VALID_LANGUAGES)}",
                )
            tenant.default_language = payload.default_language

        if payload.welcome_message is not None:
            tenant.welcome_message = payload.welcome_message.strip() or None

        if payload.system_prompt_override is not None:
            tenant.system_prompt_override = payload.system_prompt_override.strip() or None

        if payload.business_hours_enabled is not None:
            tenant.business_hours_enabled = 1 if payload.business_hours_enabled else 0

        if payload.business_hours_start is not None:
            start = payload.business_hours_start.strip()
            if not _is_valid_time(start):
                raise HTTPException(status_code=422, detail="invalid_business_hours_start: expected HH:MM")
            tenant.business_hours_start = start

        if payload.business_hours_end is not None:
            end = payload.business_hours_end.strip()
            if not _is_valid_time(end):
                raise HTTPException(status_code=422, detail="invalid_business_hours_end: expected HH:MM")
            tenant.business_hours_end = end

        if payload.business_hours_timezone is not None:
            tz = payload.business_hours_timezone.strip()
            if not tz:
                raise HTTPException(status_code=422, detail="business_hours_timezone_cannot_be_empty")
            tenant.business_hours_timezone = tz

        if payload.business_days is not None:
            days = payload.business_days.strip()
            if not days:
                raise HTTPException(status_code=422, detail="business_days_cannot_be_empty")
            tenant.business_days = days

        if payload.out_of_hours_message is not None:
            tenant.out_of_hours_message = payload.out_of_hours_message.strip() or None

        if payload.fallback_escalation_mode is not None:
            if payload.fallback_escalation_mode not in VALID_ESCALATION_MODES:
                raise HTTPException(
                    status_code=422,
                    detail=f"invalid_fallback_escalation_mode: must be one of {sorted(VALID_ESCALATION_MODES)}",
                )
            tenant.fallback_escalation_mode = payload.fallback_escalation_mode

        if payload.fallback_phone is not None:
            phone_val = payload.fallback_phone.strip()
            if phone_val:
                try:
                    tenant.fallback_phone = normalize_e164(phone_val)
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail="invalid_fallback_phone: must be valid E.164") from exc
            else:
                tenant.fallback_phone = None

        if payload.fallback_email is not None:
            email_val = payload.fallback_email.strip()
            if email_val:
                if "@" not in email_val or "." not in email_val.split("@")[-1]:
                    raise HTTPException(status_code=422, detail="invalid_fallback_email")
                tenant.fallback_email = email_val
            else:
                tenant.fallback_email = None

        if payload.max_verification_failures is not None:
            if not (1 <= payload.max_verification_failures <= 5):
                raise HTTPException(
                    status_code=422,
                    detail="max_verification_failures_must_be_between_1_and_5",
                )
            tenant.max_verification_failures = payload.max_verification_failures

        # Invalidate prompt cache immediately so the next call uses the updated configuration
        clear_tenant_prompt_cache(tenant.id)

        log.info(
            "admin.tenant_agent_settings_updated",
            tenant_id=tenant.id,
            actor_user_id=actor.user_id,
            voice_persona=tenant.voice_persona,
            language=tenant.default_language,
        )

        return TenantAgentSettingsOut(
            tenant_id=tenant.id,
            name=tenant.name,
            agent_name=tenant.agent_name or "Vaani",
            voice_persona=tenant.voice_persona or "professional",
            default_language=tenant.default_language or "en",
            welcome_message=tenant.welcome_message,
            system_prompt_override=tenant.system_prompt_override,
            business_hours_enabled=bool(tenant.business_hours_enabled),
            business_hours_start=tenant.business_hours_start or "09:00",
            business_hours_end=tenant.business_hours_end or "18:00",
            business_hours_timezone=tenant.business_hours_timezone or "Asia/Kolkata",
            business_days=tenant.business_days or "mon,tue,wed,thu,fri",
            out_of_hours_message=tenant.out_of_hours_message,
            fallback_escalation_mode=tenant.fallback_escalation_mode or "human_callback",
            fallback_phone=tenant.fallback_phone,
            fallback_email=tenant.fallback_email,
            max_verification_failures=tenant.max_verification_failures or 3,
        )


@tenant_settings_router.get("/{tenant_id}/telephony")
def get_tenant_telephony_settings(tenant_id: str, request: Request) -> dict[str, Any]:
    """Return the tenant's exact-DID routing and redacted PIN posture."""
    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        phone_rows = db.execute(
            select(TenantPhoneNumber)
            .where(TenantPhoneNumber.tenant_id == tenant_id)
            .order_by(TenantPhoneNumber.phone_number)
        ).scalars().all()
        contacts = db.execute(
            select(Supplier)
            .where(Supplier.tenant_id == tenant_id, Supplier.active == 1)
            .order_by(Supplier.name)
        ).scalars().all()
        return {
            "tenant_id": tenant_id,
            "routing_mode": "exact_did",
            "phone_numbers": [_phone_number_summary(row) for row in phone_rows],
            "verification_contacts": [
                {
                    "supplier_id": row.id,
                    "name": row.name,
                    "phone_masked": _masked_phone(row.phone),
                    "pin_configured": row.pin_configured,
                    "pin_updated_at": row.pin_updated_at.isoformat() if row.pin_updated_at else None,
                    "requires_rotation": bool(row.auth_pin and not row.auth_pin_hash),
                    "locked": _is_pin_locked(row),
                }
                for row in contacts
            ],
        }


@router.get("/tenants/{tenant_id}/phone-numbers")
def list_tenant_phone_numbers(tenant_id: str, request: Request) -> list[dict[str, Any]]:
    """List only this tenant's inbound routing rules; no credential data is returned."""
    with session_scope() as db:
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        rows = db.execute(
            select(TenantPhoneNumber)
            .where(TenantPhoneNumber.tenant_id == tenant_id)
            .order_by(TenantPhoneNumber.phone_number)
        ).scalars().all()
        return [_phone_number_summary(row) for row in rows]


@tenant_settings_router.post("/{tenant_id}/phone-numbers")
@router.post("/tenants/{tenant_id}/phone-numbers")
def map_phone_number_to_tenant(
    tenant_id: str,
    payload: PhoneNumberMapIn,
    request: Request,
) -> dict[str, Any]:
    """Create or update an exact inbound route without allowing tenant takeover."""
    try:
        clean_phone = normalize_e164(payload.phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="tenant_not_found")
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
        existing = db.get(TenantPhoneNumber, clean_phone)
        if existing and existing.tenant_id != tenant_id:
            raise HTTPException(status_code=409, detail="phone_number_owned_by_another_tenant")
        if existing:
            existing.label = payload.label or existing.label
            existing.provider = payload.provider
            existing.verification_mode = payload.verification_mode
            existing.route_language = payload.route_language
            existing.active = int(payload.active)
            row = existing
        else:
            row = TenantPhoneNumber(
                phone_number=clean_phone,
                tenant_id=tenant_id,
                label=payload.label or f"{tenant.name} Support Line",
                provider=payload.provider,
                verification_mode=payload.verification_mode,
                route_language=payload.route_language,
                active=int(payload.active),
            )
            db.add(row)
        db.flush()
        log.info("admin.phone_mapped", tenant_id=tenant_id, provider=row.provider)
        return {"ok": True, **_phone_number_summary(row)}


@tenant_settings_router.patch("/{tenant_id}/phone-numbers/{phone_number}")
@router.patch("/tenants/{tenant_id}/phone-numbers/{phone_number}")
def update_tenant_phone_number(
    tenant_id: str,
    phone_number: str,
    payload: PhoneNumberUpdateIn,
    request: Request,
) -> dict[str, Any]:
    """Update an automated route policy as a tenant owner."""
    try:
        clean_phone = normalize_e164(phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with session_scope() as db:
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
        row = db.execute(
            select(TenantPhoneNumber).where(
                TenantPhoneNumber.tenant_id == tenant_id,
                TenantPhoneNumber.phone_number == clean_phone,
            )
        ).scalars().first()
        if row is None:
            raise HTTPException(status_code=404, detail="phone_number_not_found")
        changes = payload.model_dump(exclude_unset=True)
        if "active" in changes:
            changes["active"] = int(changes["active"])
        for key, value in changes.items():
            setattr(row, key, value)
        db.flush()
        log.info("admin.phone_route_updated", tenant_id=tenant_id, provider=row.provider)
        return {"ok": True, **_phone_number_summary(row)}


@tenant_settings_router.delete("/{tenant_id}/phone-numbers/{phone_number}")
def deactivate_tenant_phone_number(
    tenant_id: str,
    phone_number: str,
    request: Request,
) -> dict[str, Any]:
    """Deactivate a tenant route without deleting its ownership/audit history."""
    try:
        clean_phone = normalize_e164(phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with session_scope() as db:
        require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
        row = db.execute(
            select(TenantPhoneNumber).where(
                TenantPhoneNumber.tenant_id == tenant_id,
                TenantPhoneNumber.phone_number == clean_phone,
            )
        ).scalars().first()
        if row is None:
            raise HTTPException(status_code=404, detail="phone_number_not_found")
        row.active = 0
        row.updated_at = datetime.now(timezone.utc)
        db.flush()
        log.info("admin.phone_route_deactivated", tenant_id=tenant_id, provider=row.provider)
        return {"ok": True, **_phone_number_summary(row)}


# ---------- Caller verification PINs ----------


@router.get("/tenants/{tenant_id}/caller-pins")
@router.get("/tenants/{tenant_id}/verification-pins")
def list_caller_pin_statuses(tenant_id: str, request: Request) -> list[dict[str, Any]]:
    """Return redacted per-contact PIN status to authorized tenant members."""
    with session_scope() as db:
        require_tenant_role(
            request,
            db,
            tenant_id=tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
            allow_demo=True,
        )
        rows = db.execute(
            select(Supplier)
            .where(Supplier.tenant_id == tenant_id)
            .order_by(Supplier.name)
        ).scalars().all()
        return [
            {
                "supplier_id": row.id,
                "name": row.name,
                "pin_configured": row.pin_configured,
                "phone_masked": _masked_phone(row.phone),
                "pin_updated_at": row.pin_updated_at.isoformat() if row.pin_updated_at else None,
                "requires_rotation": bool(row.auth_pin and not row.auth_pin_hash),
                "locked": _is_pin_locked(row),
            }
            for row in rows
        ]


@tenant_settings_router.put("/{tenant_id}/caller-verification/{supplier_id}/pin")
@router.put("/tenants/{tenant_id}/suppliers/{supplier_id}/caller-pin")
@router.put("/tenants/{tenant_id}/suppliers/{supplier_id}/verification-pin")
def set_caller_pin(
    tenant_id: str,
    supplier_id: str,
    payload: CallerPinSetIn,
    request: Request,
) -> dict[str, Any]:
    """Set a caller PIN as an owner, storing only a salted PBKDF2 hash."""
    with session_scope() as db:
        actor = require_tenant_role(request, db, tenant_id=tenant_id, allowed_roles={ROLE_OWNER})
        supplier = db.execute(
            select(Supplier).where(
                Supplier.tenant_id == tenant_id,
                Supplier.id == supplier_id,
            )
        ).scalars().first()
        if supplier is None:
            raise HTTPException(status_code=404, detail="supplier_not_found")
        if not isinstance(payload.pin, str) or not isinstance(payload.confirm_pin, str):
            raise HTTPException(status_code=422, detail="pin_and_confirmation_required")
        if payload.pin != payload.confirm_pin:
            raise HTTPException(status_code=422, detail="pin_confirmation_mismatch")
        try:
            encoded_pin = hash_pin(payload.pin)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="pin_must_be_4_to_8_digits") from exc
        supplier.auth_pin_hash = encoded_pin
        supplier.auth_pin = None
        supplier.pin_updated_at = datetime.now(timezone.utc)
        # An owner-initiated reset is a deliberate credential rotation; it must
        # also clear any persistent brute-force lockout so the new PIN works
        # immediately rather than staying locked from the prior credential.
        supplier.pin_failed_attempts = 0
        supplier.pin_locked_until = None
        log.info(
            "admin.caller_pin_updated",
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            actor_user_id=actor.user_id,
        )
        return {"ok": True, "supplier_id": supplier_id, "pin_configured": True}


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
