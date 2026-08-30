"""SQLite (dev) / Postgres (prod) data layer.

Both sync and async engines — sync for REST routes (FastAPI runs them in a
thread pool), async for the agent tool functions that run inside async handlers.

Single declarative base — schema created via `Base.metadata.create_all`.
Supports multi-tenant isolation via `tenant_id` foreign keys.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from typing import AsyncIterator, Iterator

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    inspect,
    Text,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from .config import get_settings


log = logging.getLogger(__name__)


_settings = get_settings()


def _driver_hint(url: str, exc: ModuleNotFoundError) -> str:
    """Turn an opaque missing-driver ImportError into something actionable.

    SQLAlchemy imports the DBAPI eagerly when the engine is constructed, so a
    missing driver blows up at *import* time of this module — long before any
    query runs. Every module imports `db`, so the whole application fails to
    start with nothing but `No module named 'psycopg2'` to go on.
    """
    missing = str(exc).split("'")[-2] if "'" in str(exc) else str(exc)
    return (
        f"Database driver {missing!r} is not installed, so the engine for "
        f"{url.split('://', 1)[0]!r} cannot be created.\n"
        "This project needs BOTH drivers for Postgres:\n"
        "  psycopg2-binary  — the SYNC engine used by the dashboard REST routes\n"
        "  asyncpg          — the ASYNC engine used by the agent tools\n"
        "Fix: pip install -r apps/api/requirements.txt (and rebuild the image)."
    )


def _clean_db_url(raw_url: str) -> str:
    if not raw_url or not isinstance(raw_url, str) or raw_url.strip() == "":
        return "sqlite:////tmp/voxflow-data/voxflow.db"
    val = raw_url.strip()
    if val.startswith("http://") or val.startswith("https://"):
        data_dir = os.getenv("DATA_DIR", "/tmp/voxflow-data")
        os.makedirs(data_dir, exist_ok=True)
        log.warning(
            "DATABASE_URL was set to an HTTP/HTTPS URL (%s) instead of postgresql://. "
            "Falling back to local SQLite to avoid dialect errors.",
            val,
        )
        return f"sqlite:///{data_dir}/voxflow.db"
    if val.startswith("postgres://"):
        return val.replace("postgres://", "postgresql://", 1)
    return val


_db_url = _clean_db_url(_settings.database_url)

try:
    _engine = create_engine(
        _db_url,
        connect_args={"check_same_thread": False} if _db_url.startswith("sqlite") else {},
        echo=False,
        future=True,
    )
except ModuleNotFoundError as e:  # pragma: no cover - exercised by test_db_drivers
    raise RuntimeError(_driver_hint(_db_url, e)) from e
except Exception as e:
    log.error("Failed to create engine for %s: %s. Using SQLite fallback.", _db_url, e)
    _db_url = "sqlite:////tmp/voxflow-data/voxflow.db"
    _engine = create_engine(
        _db_url,
        connect_args={"check_same_thread": False},
        echo=False,
        future=True,
    )

SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Async engine — for agent tool functions inside async handlers
def _async_db_url(url: str) -> str:
    cleaned = _clean_db_url(url)
    if cleaned.startswith("sqlite"):
        return cleaned.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if cleaned.startswith("postgresql://"):
        return cleaned.replace("postgresql://", "postgresql+asyncpg://", 1)
    return cleaned


def _pooled_url(url: str) -> str:
    """DEPRECATED no-op. Put the full pooler URL in DATABASE_URL instead."""
    return _clean_db_url(url)

_async_url = _async_db_url(_settings.database_url)
_async_engine_options = {"poolclass": NullPool} if _async_url.startswith("sqlite") else {}

try:
    _async_engine = create_async_engine(
        _async_url,
        echo=False,
        future=True,
        **_async_engine_options,
    )
except ModuleNotFoundError as e:  # pragma: no cover - exercised by test_db_drivers
    raise RuntimeError(_driver_hint(_settings.database_url, e)) from e
except Exception as e:
    log.error("Failed to create async engine: %s. Using async SQLite fallback.", e)
    _async_engine = create_async_engine(
        "sqlite+aiosqlite:////tmp/voxflow-data/voxflow.db",
        echo=False,
        future=True,
        poolclass=NullPool,
    )

AsyncSessionLocal = async_sessionmaker(bind=_async_engine, autoflush=False, expire_on_commit=False)


async def close_db_engines() -> None:
    """Release database pools during application shutdown."""
    await _async_engine.dispose()
    _engine.dispose()
    # Let aiosqlite's worker report its final close callback before the loop ends.
    await asyncio.sleep(0.05)


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Models ----------


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    active: Mapped[int] = mapped_column(Integer, default=1)
    agent_name: Mapped[str] = mapped_column(String(64), default="Vaani")
    system_prompt_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_language: Mapped[str] = mapped_column(String(8), default="en")
    webhook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    plan: Mapped[str] = mapped_column(String(32), default="pro")
    total_minutes_used: Mapped[float] = mapped_column(Float, default=0.0)
    voice_persona: Mapped[str] = mapped_column(String(32), default="professional", server_default=text("'professional'"))
    business_hours_enabled: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    business_hours_start: Mapped[str] = mapped_column(String(8), default="09:00", server_default=text("'09:00'"))
    business_hours_end: Mapped[str] = mapped_column(String(8), default="18:00", server_default=text("'18:00'"))
    business_hours_timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", server_default=text("'Asia/Kolkata'"))
    business_days: Mapped[str] = mapped_column(String(64), default="mon,tue,wed,thu,fri", server_default=text("'mon,tue,wed,thu,fri'"))
    out_of_hours_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fallback_escalation_mode: Mapped[str] = mapped_column(String(32), default="human_callback", server_default=text("'human_callback'"))
    fallback_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fallback_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_verification_failures: Mapped[int] = mapped_column(Integer, default=3, server_default=text("3"))
    escalation_sla_minutes: Mapped[int] = mapped_column(Integer, default=60, server_default=text("60"))
    # Self-serve per-tenant Google Sheets mirror configuration
    google_sheet_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    google_sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sheet_tab: Mapped[str] = mapped_column(String(64), default="Call Log", server_default=text("'Call Log'"))
    google_sheet_email_tab: Mapped[str] = mapped_column(String(64), default="Email Log", server_default=text("'Email Log'"))
    google_sheet_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    google_sheet_connected_by_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    google_sheet_status: Mapped[str] = mapped_column(String(32), default="disconnected", server_default=text("'disconnected'"))
    call_retention_days: Mapped[int] = mapped_column(Integer, default=90, server_default=text("90"))
    transcript_retention_days: Mapped[int] = mapped_column(Integer, default=30, server_default=text("30"))
    pii_masking_enabled: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    data_residency_region: Mapped[str] = mapped_column(String(32), default="eu-west-2", server_default=text("'eu-west-2'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class TenantMember(Base):
    """Tenant-scoped application membership linked to an external identity.

    The platform never trusts a browser-selected tenant or mutable Supabase user
    metadata for authorization. A real bearer-token subject must have one active
    row in this ledger for the requested tenant. Pending invitations retain only
    a normalized email hash until the authenticated recipient accepts them.
    """

    __tablename__ = "tenant_members"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_member_user"),
        UniqueConstraint("tenant_id", "subject_email_hash", name="uq_tenant_member_email_hash"),
        Index("ix_tenant_member_user_status", "user_id", "status"),
        Index("ix_tenant_member_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    subject_email_hash: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16), default="viewer", index=True)  # owner | operator | viewer
    status: Mapped[str] = mapped_column(String(16), default="invited", index=True)  # invited | active | revoked
    invited_by: Mapped[str] = mapped_column(String(128), default="")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    name: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    city: Mapped[str] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(128))
    pincode: Mapped[str] = mapped_column(String(16))
    contact_person: Mapped[str] = mapped_column(String(255), default="")
    gstin: Mapped[str] = mapped_column(String(32), default="")
    # Legacy plaintext is retained only so pre-Day-46 rows can be verified and
    # upgraded in place. New and updated credentials use auth_pin_hash only.
    auth_pin: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    auth_pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    pin_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Persistent, per-contact lockout state. A `CallSession`-scoped attempt
    # counter alone cannot stop brute forcing across many fresh sessions (a new
    # call, or a new unauthenticated /agent/run request, always starts at zero
    # attempts). These two columns survive across sessions/calls so guessing a
    # 4–8 digit PIN costs an attacker real lockout time, not just a new call.
    pin_failed_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    pin_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Which side of the trade this contact sits on.
    # customer = they buy from us | supplier = they sell to us | both
    contact_type: Mapped[str] = mapped_column(String(16), default="customer", index=True)
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="supplier", cascade="all,delete")

    @property
    def pin_configured(self) -> bool:
        return bool(self.auth_pin_hash or self.auth_pin)


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), primary_key=True, default="varun")
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(128))
    pack_size: Mapped[str] = mapped_column(String(64))
    mrp_inr: Mapped[float] = mapped_column(Float)


class Stock(Base):
    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    sku: Mapped[str] = mapped_column(String(64), index=True)
    warehouse: Mapped[str] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("suppliers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | confirmed | shipped | delivered | cancelled
    items_json: Mapped[str] = mapped_column(Text)  # JSON list of {sku, qty}
    total_qty: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    # --- PO acknowledgement / dispatch tracking (customer-support flow) ---
    # The customer's own PO number on their side, e.g. "VB/PO/2026/0912".
    customer_po_ref: Mapped[str] = mapped_column(String(128), default="", index=True)
    po_signed: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unsigned, 1 = signed
    po_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    po_signed_by: Mapped[str] = mapped_column(String(255), default="")
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    supplier: Mapped[Supplier] = relationship(back_populates="orders")


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    order_id: Mapped[str] = mapped_column(String(64), ForeignKey("orders.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="booked")  # booked | in_transit | out_for_delivery | delivered | delayed
    carrier: Mapped[str] = mapped_column(String(128), default="")
    tracking_no: Mapped[str] = mapped_column(String(128), default="")
    expected_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    history_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of events


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    supplier_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("suppliers.id"), nullable=True)
    caller_phone: Mapped[str] = mapped_column(String(32), default="")
    caller_name: Mapped[str] = mapped_column(String(255), default="")
    language: Mapped[str] = mapped_column(String(8), default="en")
    intent: Mapped[str] = mapped_column(String(64), default="")
    outcome: Mapped[str] = mapped_column(String(64), default="")
    escalated: Mapped[int] = mapped_column(Integer, default=0)
    transcript_json: Mapped[str] = mapped_column(Text, default="[]")
    actions_json: Mapped[str] = mapped_column(Text, default="[]")
    # --- Structured call outcome (written by the log_call_outcome tool) ---
    # Why they called, in the caller's own framing.
    reason: Mapped[str] = mapped_column(Text, default="")
    # What the agent actually told/did for them.
    solution: Mapped[str] = mapped_column(Text, default="")
    # resolved | partial | unresolved
    resolution_status: Mapped[str] = mapped_column(String(16), default="", index=True)
    # happy | neutral | unhappy
    satisfaction: Mapped[str] = mapped_column(String(16), default="", index=True)
    follow_up_required: Mapped[int] = mapped_column(Integer, default=0)
    # Filled in by staff from the dashboard after following up on an escalation.
    staff_resolution: Mapped[str] = mapped_column(Text, default="")
    staff_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Day 48: Escalation Lifecycle, Priority, Assignee, and SLA deadline
    escalation_priority: Mapped[str] = mapped_column(String(16), default="medium", server_default=text("'medium'"))
    escalation_status: Mapped[str] = mapped_column(String(16), default="none", server_default=text("'none'"), index=True)
    assigned_to_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    resolved_by_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolution_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Whether this call's outcome row reached Google Sheets.
    sheet_synced: Mapped[int] = mapped_column(Integer, default=0)
    # Day 42: mean server-side processing time per agent turn (ms), 0 if unknown.
    avg_turn_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    # Twilio call recording audio URL (if recorded)
    recording_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verified: Mapped[int] = mapped_column(Integer, default=0)


class TenantPhoneNumber(Base):
    """Owns one exact E.164 inbound DID and its automated call policy."""

    __tablename__ = "tenant_phone_numbers"
    __table_args__ = (
        # This constraint is deliberately looser than the Postgres migration's
        # `^\+[1-9][0-9]{7,14}$` regex CHECK (016_telephony_routing_and_
        # caller_pins.sql): SQLite CHECK constraints cannot use regular
        # expressions. The strict format is authoritatively enforced by
        # `services.telephony_routing.normalize_e164`, which every write path
        # (admin routes, provisioning, CSV ingestion, the map_phone CLI) calls
        # before persisting a phone number on either database backend; this
        # constraint is only a coarse SQLite-side defense-in-depth backstop.
        CheckConstraint(
            "phone_number LIKE '+%' AND length(phone_number) BETWEEN 9 AND 16",
            name="ck_tenant_phone_e164",
        ),
        CheckConstraint("provider IN ('connect', 'twilio', 'telnyx')", name="ck_tenant_phone_provider"),
        CheckConstraint("verification_mode IN ('standard', 'enhanced')", name="ck_tenant_phone_verification_mode"),
        CheckConstraint("route_language IN ('tenant_default', 'en', 'hi')", name="ck_tenant_phone_route_language"),
        Index("ix_tenant_phone_provider_active", "provider", "phone_number", "active"),
        Index("ix_tenant_phone_tenant_active", "tenant_id", "active"),
    )

    phone_number: Mapped[str] = mapped_column(String(32), primary_key=True)  # E.164, e.g. +14155551234
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    label: Mapped[str] = mapped_column(String(128), default="")
    provider: Mapped[str] = mapped_column(String(32), default="twilio", server_default="twilio")
    verification_mode: Mapped[str] = mapped_column(String(16), default="standard", server_default="standard")
    route_language: Mapped[str] = mapped_column(String(16), default="tenant_default", server_default="tenant_default")
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    supplier_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("suppliers.id"), nullable=True)
    datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    purpose: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | confirmed | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class WorksheetLog(Base):
    __tablename__ = "worksheet_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    worksheet_name: Mapped[str] = mapped_column(String(128))
    action_type: Mapped[str] = mapped_column(String(32))  # append | update | delete
    row_data_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    channel: Mapped[str] = mapped_column(String(32))  # email | whatsapp
    recipient: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="sent")  # sent | failed | received | summarized
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AgentState(Base):
    __tablename__ = "agent_states"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    value_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class OutboundCampaign(Base):
    __tablename__ = "outbound_campaigns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    name: Mapped[str] = mapped_column(String(255))
    campaign_type: Mapped[str] = mapped_column(String(64), default="delayed_shipment")  # delayed_shipment | po_confirmation | dock_reminder | generic
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft | active | running | paused | completed
    total_targets: Mapped[int] = mapped_column(Integer, default=0)
    successful_calls: Mapped[int] = mapped_column(Integer, default=0)
    failed_calls: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class CampaignQueue(Base):
    __tablename__ = "campaign_queue"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(String(64), ForeignKey("outbound_campaigns.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    recipient_phone: Mapped[str] = mapped_column(String(32))
    recipient_name: Mapped[str] = mapped_column(String(255), default="")
    context_data_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued | dialing | answered | no_answer | completed | failed | cancelled
    attempts_made: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transcript_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ---------- Day 30 campaign policy controls ----------


class TenantCampaignPolicy(Base):
    """One explicit, tenant-scoped outbound-campaign policy configuration."""

    __tablename__ = "tenant_campaign_policies"

    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), primary_key=True)
    timezone_name: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    calling_window_start: Mapped[str] = mapped_column(String(5), default="09:00")
    calling_window_end: Mapped[str] = mapped_column(String(5), default="20:00")
    daily_call_limit: Mapped[int] = mapped_column(Integer, default=100)
    max_in_flight: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ---------- Privacy lifecycle controls ----------


class TenantPrivacyPolicy(Base):
    """Tenant-owned retention policy with privacy-preserving defaults.

    The policy drives previews and future reviewed purge jobs. It never enables
    provider recording retrieval or external disclosure on its own.
    """

    __tablename__ = "tenant_privacy_policies"

    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), primary_key=True)
    call_transcript_retention_days: Mapped[int] = mapped_column(Integer, default=30)
    communication_retention_days: Mapped[int] = mapped_column(Integer, default=30)
    recording_retention_days: Mapped[int] = mapped_column(Integer, default=0)
    updated_by: Mapped[str] = mapped_column(String(128), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class PrivacyRequest(Base):
    """Redacted request ledger for access exports, deletion review, and demo reset.

    ``subject_hash`` is a one-way digest of the supplied subject reference. Raw
    phone numbers, email addresses, transcripts, and customer account data are
    deliberately excluded from this workflow record.
    """

    __tablename__ = "privacy_requests"
    __table_args__ = (
        Index("ix_privacy_request_tenant_status", "tenant_id", "status"),
        Index("ix_privacy_request_subject_hash", "tenant_id", "subject_hash"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    request_type: Mapped[str] = mapped_column(String(32), index=True)  # access_export | deletion | demo_reset
    subject_hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending_human_review", index=True)
    requested_by: Mapped[str] = mapped_column(String(128), default="")
    review_note: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


# ---------- Day 35 controlled pilot readiness ----------


class PilotConfiguration(Base):
    """Versioned, tenant-scoped readiness contract for one controlled pilot.

    It deliberately stores no recipient phone numbers or escalation contact
    channels. Those remain in the consent and external staff systems. A row is
    only *eligible* when it is approved, unexpired, covered by the environment
    allow-list, and has a reviewed redacted cohort ledger.
    """

    __tablename__ = "pilot_configurations"

    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), primary_key=True)
    pilot_id: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)  # draft | approved | paused | expired | rolled_back
    cohort_id: Mapped[str] = mapped_column(String(96), index=True)
    cohort_size: Mapped[int] = mapped_column(Integer, default=0)
    timezone_name: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    calling_window_start: Mapped[str] = mapped_column(String(5), default="09:00")
    calling_window_end: Mapped[str] = mapped_column(String(5), default="20:00")
    daily_call_limit: Mapped[int] = mapped_column(Integer, default=1)
    max_in_flight: Mapped[int] = mapped_column(Integer, default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    primary_escalation_owner: Mapped[str] = mapped_column(String(255), default="")
    backup_escalation_owner: Mapped[str] = mapped_column(String(255), default="")
    acknowledgement_timeout_minutes: Mapped[int] = mapped_column(Integer, default=15)
    metric_contract_version: Mapped[str] = mapped_column(String(32), default="day35-v1")
    approved_by: Mapped[str] = mapped_column(String(255), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class PilotCohortMember(Base):
    """One reviewed recipient admission represented only by a stable SHA-256 hash."""

    __tablename__ = "pilot_cohort_members"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cohort_id", "recipient_hash", name="uq_pilot_cohort_recipient"),
        Index("ix_pilot_cohort_member_lookup", "tenant_id", "cohort_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    cohort_id: Mapped[str] = mapped_column(String(96), index=True)
    recipient_hash: Mapped[str] = mapped_column(String(64), index=True)
    consent_evidence_ref: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="approved", index=True)  # approved | withdrawn | excluded
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PilotSecurityIncident(Base):
    """Tenant-scoped confirmed security finding for a pilot scorecard.

    This ledger intentionally records classification and bounded summary only;
    raw callback content, secrets, contact data, and access tokens never belong
    in pilot reporting.
    """

    __tablename__ = "pilot_security_incidents"
    __table_args__ = (Index("ix_pilot_security_incident_tenant_created", "tenant_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    pilot_id: Mapped[str] = mapped_column(String(96), index=True)
    category: Mapped[str] = mapped_column(String(96), index=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), default="confirmed", index=True)  # suspected | confirmed | resolved
    summary: Mapped[str] = mapped_column(String(512), default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PilotOperationalEvidence(Base):
    """Redacted immutable Day 36 evidence for a pilot preflight or hold point.

    Evidence rows never contain phone numbers, transcripts, webhook bodies,
    provider credentials, or raw durable-job payloads. The table supports an
    auditable same-cohort decision trail but does not start, pause, or expand a
    campaign by itself.
    """

    __tablename__ = "pilot_operational_evidence"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "pilot_id",
            "pilot_version",
            "evidence_kind",
            "evidence_key",
            name="uq_pilot_operational_evidence_key",
        ),
        Index("ix_pilot_operational_evidence_tenant_created", "tenant_id", "created_at"),
        Index("ix_pilot_operational_evidence_pilot_kind_created", "pilot_id", "evidence_kind", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    pilot_id: Mapped[str] = mapped_column(String(96), index=True)
    pilot_version: Mapped[int] = mapped_column(Integer, default=1)
    evidence_kind: Mapped[str] = mapped_column(String(32), index=True)  # preflight | hold_point | pause | rollback
    evidence_key: Mapped[str] = mapped_column(String(128))
    decision: Mapped[str] = mapped_column(String(48), index=True)  # continue_same_cohort | pause | rollback_requested | blocked
    reason_code: Mapped[str] = mapped_column(String(128), default="")
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    recorded_by: Mapped[str] = mapped_column(String(128), default="trusted_operator_service")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ReliabilitySLO(Base):
    """A tenant-scoped reliability objective used only for read-only scorecards.

    SLO definitions contain aggregate thresholds and never include recipient
    identifiers, transcript data, callback bodies, provider credentials, or a
    control that can activate any worker.
    """

    __tablename__ = "reliability_slos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "metric_type", name="uq_reliability_slo_tenant_metric"),
        Index("ix_reliability_slo_tenant_active", "tenant_id", "active"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    metric_type: Mapped[str] = mapped_column(String(64), index=True)
    target_percent: Mapped[float] = mapped_column(Float, default=100.0)
    window_hours: Mapped[int] = mapped_column(Integer, default=24)
    comparison: Mapped[str] = mapped_column(String(16), default="minimum")  # minimum | maximum
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class DrillResult(Base):
    """Immutable aggregate-only receipt from a deterministic safety drill.

    Drill results document an in-memory, database-only fault fixture. They do
    not enqueue work, claim leases, enable workers, contact providers, or store
    raw payloads, phone numbers, transcripts, secrets, or callback content.
    """

    __tablename__ = "drill_results"
    __table_args__ = (
        UniqueConstraint("tenant_id", "fixture_type", "execution_key", name="uq_drill_result_execution"),
        Index("ix_drill_result_tenant_created", "tenant_id", "created_at"),
        Index("ix_drill_result_tenant_fixture", "tenant_id", "fixture_type", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    fixture_type: Mapped[str] = mapped_column(String(64), index=True)
    fixture_version: Mapped[str] = mapped_column(String(32), default="day37-v1")
    execution_key: Mapped[str] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(32), index=True)  # passed | failed | blocked
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    recovery_summary: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RecipientCampaignPreference(Base):
    """Current recipient consent and opt-out state, isolated by tenant and phone."""

    __tablename__ = "recipient_campaign_preferences"
    __table_args__ = (UniqueConstraint("tenant_id", "recipient_phone", name="uq_recipient_campaign_preference"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    recipient_phone: Mapped[str] = mapped_column(String(32), index=True)
    consent_status: Mapped[str] = mapped_column(String(32), default="granted")  # granted | withdrawn | unknown
    consent_purpose: Mapped[str] = mapped_column(String(64), default="outbound_campaign")
    opted_out: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(128), default="tenant_default")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class TenantDailyDispatchUsage(Base):
    """Atomic per-tenant local-day capacity and daily dispatch budget counters."""

    __tablename__ = "tenant_daily_dispatch_usage"
    __table_args__ = (UniqueConstraint("tenant_id", "local_date", name="uq_tenant_dispatch_usage_day"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    local_date: Mapped[str] = mapped_column(String(10), index=True)
    reserved_calls: Mapped[int] = mapped_column(Integer, default=0)
    active_dispatches: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class CampaignDispatchReservation(Base):
    """One active/settled policy capacity reservation per durable campaign job."""

    __tablename__ = "campaign_dispatch_reservations"
    __table_args__ = (UniqueConstraint("job_id", name="uq_campaign_dispatch_reservation_job"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("job_runs.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    local_date: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active | released | settled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CampaignPolicyDecision(Base):
    """Immutable policy-evaluation audit record for an individual target attempt."""

    __tablename__ = "campaign_policy_decisions"
    __table_args__ = (Index("ix_campaign_policy_decision_target", "tenant_id", "campaign_queue_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("job_runs.id"), index=True)
    campaign_id: Mapped[str] = mapped_column(String(64), ForeignKey("outbound_campaigns.id"), index=True)
    campaign_queue_id: Mapped[str] = mapped_column(String(64), ForeignKey("campaign_queue.id"), index=True)
    decision: Mapped[str] = mapped_column(String(32), index=True)  # allowed | deferred | cancelled
    reason_code: Mapped[str] = mapped_column(String(128), index=True)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    next_eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------- Durable jobs and transactional outbox (Day 25) ----------


class JobRun(Base):
    """Durable unit of worker-owned work.

    The worker implementation added on Day 26 atomically claims eligible rows,
    leases them, and records attempts. The API writes intent only; it never
    performs the side effect inline.
    """

    __tablename__ = "job_runs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_job_runs_tenant_idempotency"),
        Index("ix_job_runs_claim", "status", "next_run_at", "priority", "scheduled_at"),
        Index("ix_job_runs_lease", "lease_expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    job_type: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default="ready", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=6)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class JobOutbox(Base):
    """Transactional event record converted into a JobRun by the future relay."""

    __tablename__ = "job_outbox"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_job_outbox_tenant_idempotency"),
        Index("ix_job_outbox_unpublished", "published_at", "created_at"),
        Index("ix_job_outbox_claim", "published_at", "relay_lease_expires_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(128))
    aggregate_id: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    idempotency_key: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    relay_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    relay_lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publish_attempt: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class SideEffectIntent(Base):
    """Immutable Day 34 external-operation intent, owned by one durable job.

    The row contains only a payload hash and trusted aggregate identifiers. Raw
    message bodies, sheet rows, recording bytes, secrets, signatures, and phone
    numbers stay in their existing business tables and never enter the job or
    side-effect ledger.
    """

    __tablename__ = "side_effect_intents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_side_effect_intent_idempotency"),
        UniqueConstraint("job_id", name="uq_side_effect_intent_job"),
        Index("ix_side_effect_intent_tenant_type_status", "tenant_id", "effect_type", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("job_runs.id"), index=True)
    effect_type: Mapped[str] = mapped_column(String(128), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(128))
    aggregate_id: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    result_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobAttempt(Base):
    """Immutable execution history for a durable job."""

    __tablename__ = "job_attempts"
    __table_args__ = (UniqueConstraint("job_id", "attempt_no", name="uq_job_attempts_job_attempt"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("job_runs.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    attempt_no: Mapped[int] = mapped_column(Integer)
    worker_id: Mapped[str] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(32), default="running")
    provider_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProviderOperation(Base):
    """Provider-side effect record used to prevent duplicate calls or messages."""

    __tablename__ = "provider_operations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "provider", "operation_type", "idempotency_key",
            name="uq_provider_operations_idempotency",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    operation_type: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    provider_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    request_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="requested", index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ---------- Day 32 provider callback lifecycle ----------


class ProviderEvent(Base):
    """Immutable, signature-verified provider callback applied to one operation."""

    __tablename__ = "provider_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_provider_events_provider_event"),
        Index("ix_provider_events_operation_occurred", "provider_operation_id", "occurred_at"),
        Index("ix_provider_events_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    provider_operation_id: Mapped[str] = mapped_column(String(64), ForeignKey("provider_operations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    provider_event_id: Mapped[str] = mapped_column(String(128))
    provider_call_id: Mapped[str] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload_hash: Mapped[str] = mapped_column(String(128))
    normalized_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    apply_status: Mapped[str] = mapped_column(String(32), default="applied", index=True)
    anomaly_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ProviderCallbackQuarantine(Base):
    """Safe record for a trusted-but-unmatched callback; it has no tenant linkage."""

    __tablename__ = "provider_callback_quarantines"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_provider_callback_quarantine_event"),
        Index("ix_provider_callback_quarantine_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    provider_event_id: Mapped[str] = mapped_column(String(128))
    provider_call_id: Mapped[str] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_hash: Mapped[str] = mapped_column(String(128))
    reason_code: Mapped[str] = mapped_column(String(128), default="unknown_provider_operation")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------- Day 33 provider adapter sandbox certification ----------


class ProviderCallbackAdapterAudit(Base):
    """Redacted immutable receipt for provider-adapter verification and rollout decisions.

    Raw callback bodies, signature values, telephone numbers, and secrets must
    never be placed in this model. A tenant is populated only after a normalized
    event maps to one existing stored provider operation.
    """

    __tablename__ = "provider_callback_adapter_audits"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_event_id", "payload_hash",
            name="uq_provider_callback_adapter_audit_event_payload",
        ),
        Index("ix_provider_callback_adapter_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_provider_callback_adapter_audit_provider_created", "provider", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("tenants.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    provider_event_id: Mapped[str] = mapped_column(String(128))
    provider_event_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload_hash: Mapped[str] = mapped_column(String(128))
    verification_status: Mapped[str] = mapped_column(String(32), index=True)
    normalization_status: Mapped[str] = mapped_column(String(32), index=True)
    application_status: Mapped[str] = mapped_column(String(32), index=True)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RetentionPurgeLog(Base):
    __tablename__ = "retention_purge_logs"
    __table_args__ = (
        Index("ix_retention_purge_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_retention_purge_logs_execution_type", "execution_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    purged_by_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    execution_type: Mapped[str] = mapped_column(String(32))  # automated_cron | manual_trigger
    records_scanned: Mapped[int] = mapped_column(Integer, default=0)
    calls_anonymized: Mapped[int] = mapped_column(Integer, default=0)
    transcripts_purged: Mapped[int] = mapped_column(Integer, default=0)
    dry_run: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------- Helpers ----------


def _ensure_day28_outbox_columns() -> None:
    """Upgrade legacy outbox tables for Day 28 in deployments using create_all.

    Existing managed databases predate the ORM columns, and SQLAlchemy's
    ``create_all`` never alters a table it already finds. The checked-in SQL
    migration remains the primary production migration; this idempotent startup
    safeguard prevents a partial deploy from serving a 500 before that migration
    has been applied by the hosting platform.
    """

    statements = [
        "ALTER TABLE job_outbox ADD COLUMN IF NOT EXISTS relay_owner VARCHAR(128)",
        "ALTER TABLE job_outbox ADD COLUMN IF NOT EXISTS relay_lease_expires_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE job_outbox ADD COLUMN IF NOT EXISTS publish_attempt INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE job_outbox ADD COLUMN IF NOT EXISTS last_error_code VARCHAR(128)",
        "ALTER TABLE job_outbox ADD COLUMN IF NOT EXISTS last_error_json TEXT",
        "CREATE INDEX IF NOT EXISTS ix_job_outbox_claim ON job_outbox (published_at, relay_lease_expires_at, created_at)",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS avg_turn_latency_ms INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS auth_pin_hash VARCHAR(255)",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS pin_updated_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS pin_failed_attempts INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS pin_locked_until TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE tenant_phone_numbers ADD COLUMN IF NOT EXISTS verification_mode VARCHAR(16) NOT NULL DEFAULT 'standard'",
        "ALTER TABLE tenant_phone_numbers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE",
        "UPDATE tenant_phone_numbers SET updated_at = created_at WHERE updated_at IS NULL",
        "ALTER TABLE tenant_phone_numbers ADD COLUMN IF NOT EXISTS route_language VARCHAR(16) NOT NULL DEFAULT 'tenant_default'",
        "CREATE INDEX IF NOT EXISTS ix_tenant_phone_provider_active ON tenant_phone_numbers (provider, phone_number, active)",
        "CREATE INDEX IF NOT EXISTS ix_tenant_phone_tenant_active ON tenant_phone_numbers (tenant_id, active)",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS voice_persona VARCHAR(32) NOT NULL DEFAULT 'professional'",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_hours_enabled INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_hours_start VARCHAR(8) NOT NULL DEFAULT '09:00'",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_hours_end VARCHAR(8) NOT NULL DEFAULT '18:00'",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_hours_timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata'",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_days VARCHAR(64) NOT NULL DEFAULT 'mon,tue,wed,thu,fri'",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS out_of_hours_message TEXT",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS fallback_escalation_mode VARCHAR(32) NOT NULL DEFAULT 'human_callback'",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS fallback_phone VARCHAR(32)",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS fallback_email VARCHAR(255)",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS max_verification_failures INTEGER NOT NULL DEFAULT 3",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS escalation_sla_minutes INTEGER NOT NULL DEFAULT 60",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS escalation_priority VARCHAR(16) NOT NULL DEFAULT 'medium'",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS escalation_status VARCHAR(16) NOT NULL DEFAULT 'none'",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS assigned_to_user_id VARCHAR(128)",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS resolved_by_user_id VARCHAR(128)",
        "ALTER TABLE calls ADD COLUMN IF NOT EXISTS resolution_category VARCHAR(64)",
        "CREATE INDEX IF NOT EXISTS ix_calls_escalation_status ON calls (escalation_status)",
        "CREATE INDEX IF NOT EXISTS ix_calls_sla_due_at ON calls (sla_due_at)",
    ]
    if _engine.dialect.name == "sqlite":
        # SQLite supports ADD COLUMN but not PostgreSQL's IF NOT EXISTS form.
        statements = [statement.replace(" ADD COLUMN IF NOT EXISTS", " ADD COLUMN") for statement in statements]

    with _engine.begin() as conn:
        for statement in statements:
            try:
                conn.execute(text(statement))
            except Exception as exc:
                # SQLite raises duplicate-column errors when the application is
                # restarted after a previous successful local upgrade. Postgres
                # uses IF NOT EXISTS, so any other error remains actionable.
                if _engine.dialect.name == "sqlite" and "duplicate column name" in str(exc).lower():
                    continue
                raise


def _ensure_supplier_auth_pin_nullable_sqlite() -> None:
    """Relax a legacy SQLite ``suppliers.auth_pin NOT NULL`` constraint in place.

    Pre-Day-46 local SQLite databases created ``auth_pin`` as ``NOT NULL``.
    SQLite cannot drop a NOT NULL constraint with a simple ALTER statement, so
    an untouched local database from before this change would reject every
    new supplier insert that intentionally omits a plaintext PIN. Production
    always runs PostgreSQL through the reviewed
    ``016_telephony_routing_and_caller_pins.sql`` migration, which already
    handles this with a real ``ALTER COLUMN ... DROP NOT NULL``; this path
    only protects local SQLite development databases that were not reset.
    """

    if _engine.dialect.name != "sqlite":
        return

    with _engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(suppliers)")).mappings().all()
        if not columns:
            return  # table does not exist yet; create_all() will define it correctly
        auth_pin_column = next((c for c in columns if c["name"] == "auth_pin"), None)
        if auth_pin_column is None or not auth_pin_column["notnull"]:
            return  # already nullable

        log.warning("db.sqlite_legacy_auth_pin_upgrade_started")
        existing_column_names = {c["name"] for c in columns}
        copy_columns = [
            name
            for name in (
                "id",
                "tenant_id",
                "name",
                "phone",
                "city",
                "state",
                "pincode",
                "contact_person",
                "gstin",
                "auth_pin",
                "auth_pin_hash",
                "pin_updated_at",
                "pin_failed_attempts",
                "pin_locked_until",
                "contact_type",
                "active",
                "created_at",
            )
            if name in existing_column_names
        ]
        columns_sql = ", ".join(copy_columns)

        # This engine never enables SQLite foreign-key enforcement (no
        # `PRAGMA foreign_keys=ON` connect-time listener exists anywhere in
        # this module), so a DROP/rename dance needs no FK toggle here. The
        # constraint is still declared below for schema fidelity with
        # `000_base_schema.sql` and to stay correct if that ever changes.
        conn.execute(
            text(
                "CREATE TABLE suppliers__day46_upgrade ("
                "id VARCHAR(64) NOT NULL PRIMARY KEY, "
                "tenant_id VARCHAR(64) NOT NULL, "
                "name VARCHAR(255) NOT NULL, "
                "phone VARCHAR(32) NOT NULL, "
                "city VARCHAR(128) NOT NULL, "
                "state VARCHAR(128) NOT NULL, "
                "pincode VARCHAR(16) NOT NULL, "
                "contact_person VARCHAR(255) NOT NULL DEFAULT '', "
                "gstin VARCHAR(32) NOT NULL DEFAULT '', "
                "auth_pin VARCHAR(16), "
                "auth_pin_hash VARCHAR(255), "
                "pin_updated_at DATETIME, "
                "pin_failed_attempts INTEGER NOT NULL DEFAULT 0, "
                "pin_locked_until DATETIME, "
                "contact_type VARCHAR(16) NOT NULL DEFAULT 'customer', "
                "active INTEGER NOT NULL DEFAULT 1, "
                "created_at DATETIME NOT NULL, "
                "FOREIGN KEY(tenant_id) REFERENCES tenants (id)"
                ")"
            )
        )
        conn.execute(
            text(
                f"INSERT INTO suppliers__day46_upgrade ({columns_sql}) "
                f"SELECT {columns_sql} FROM suppliers"
            )
        )
        conn.execute(text("DROP TABLE suppliers"))
        conn.execute(text("ALTER TABLE suppliers__day46_upgrade RENAME TO suppliers"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_suppliers_contact_type ON suppliers (contact_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_suppliers_name ON suppliers (name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_suppliers_phone ON suppliers (phone)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_suppliers_tenant_id ON suppliers (tenant_id)"))
        log.warning("db.sqlite_legacy_auth_pin_upgrade_completed")


def _ensure_product_composite_key_sqlite() -> None:
    """Migrate legacy SQLite ``products`` single-column PK to composite (sku, tenant_id).

    Pre-Day-45 local SQLite databases created ``products`` with ``PRIMARY KEY (sku)``.
    SQLite cannot alter a primary key in place, so an un-reset local database
    from before this change would reject duplicate SKUs across different tenants.
    """

    if _engine.dialect.name != "sqlite":
        return

    with _engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(products)")).mappings().all()
        if not columns:
            return  # table does not exist yet; create_all() will define it correctly

        pk_columns = {c["name"] for c in columns if c["pk"] > 0}
        # If already composite (both sku and tenant_id are PKs), nothing to do
        if "sku" in pk_columns and "tenant_id" in pk_columns:
            return

        log.warning("db.sqlite_legacy_product_composite_key_upgrade_started")
        existing_column_names = {c["name"] for c in columns}
        copy_columns = [
            name
            for name in (
                "sku",
                "tenant_id",
                "name",
                "category",
                "pack_size",
                "mrp_inr",
            )
            if name in existing_column_names
        ]
        columns_sql = ", ".join(copy_columns)

        conn.execute(
            text(
                "CREATE TABLE products__day46_upgrade ("
                "sku VARCHAR(64) NOT NULL, "
                "tenant_id VARCHAR(64) NOT NULL, "
                "name VARCHAR(255) NOT NULL, "
                "category VARCHAR(128) NOT NULL, "
                "pack_size VARCHAR(64) NOT NULL, "
                "mrp_inr FLOAT NOT NULL, "
                "PRIMARY KEY (sku, tenant_id), "
                "FOREIGN KEY(tenant_id) REFERENCES tenants (id)"
                ")"
            )
        )
        conn.execute(
            text(
                f"INSERT INTO products__day46_upgrade ({columns_sql}) "
                f"SELECT {columns_sql} FROM products"
            )
        )
        conn.execute(text("DROP TABLE products"))
        conn.execute(text("ALTER TABLE products__day46_upgrade RENAME TO products"))
        log.warning("db.sqlite_legacy_product_composite_key_upgrade_completed")



def _ensure_tenant_data_retention_columns_sqlite() -> None:
    """Add Day 52 retention/GDPR columns to SQLite tenants table if missing."""
    if _engine.dialect.name != "sqlite":
        return
    with _engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(tenants)")).mappings().all()
        if not columns:
            return
        existing = {c["name"] for c in columns}
        new_cols = [
            ("call_retention_days", "INTEGER DEFAULT 90"),
            ("transcript_retention_days", "INTEGER DEFAULT 30"),
            ("pii_masking_enabled", "INTEGER DEFAULT 1"),
            ("data_residency_region", "VARCHAR(32) DEFAULT 'eu-west-2'"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing:
                try:
                    conn.execute(text(f"ALTER TABLE tenants ADD COLUMN {col_name} {col_type}"))
                except Exception as e:
                    log.warning("db.sqlite_add_column_failed", column=col_name, error=str(e))


def _ensure_tenant_google_sheets_columns_sqlite() -> None:
    """Add per-tenant google sheets columns to SQLite tenants table if missing."""
    if _engine.dialect.name != "sqlite":
        return

    with _engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(tenants)")).mappings().all()
        if not columns:
            return
        existing = {c["name"] for c in columns}
        new_cols = [
            ("google_sheet_id", "VARCHAR(128)"),
            ("google_sheet_name", "VARCHAR(255)"),
            ("google_sheet_tab", "VARCHAR(64) DEFAULT 'Call Log'"),
            ("google_sheet_email_tab", "VARCHAR(64) DEFAULT 'Email Log'"),
            ("google_sheet_connected_at", "DATETIME"),
            ("google_sheet_connected_by_user_id", "VARCHAR(128)"),
            ("google_sheet_status", "VARCHAR(32) DEFAULT 'disconnected'"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing:
                try:
                    conn.execute(text(f"ALTER TABLE tenants ADD COLUMN {col_name} {col_type}"))
                except Exception as e:
                    log.warning("db.sqlite_add_column_failed", column=col_name, error=str(e))


def should_bootstrap_schema(*, mode: str, dialect_name: str) -> bool:
    """Return whether a process may apply compatibility DDL at startup.

    SQLite is intentionally self-initializing for local development and the
    isolated test suite. Production PostgreSQL must instead use the checked-in,
    reviewed SQL migrations; repeating ``create_all`` and idempotent ALTER/INDEX
    work on every Render Free wake-up adds avoidable database latency.
    """

    if mode == "always":
        return True
    if mode == "skip":
        return False
    if mode == "auto":
        return dialect_name == "sqlite"
    raise ValueError(f"unsupported database bootstrap mode: {mode}")


def verify_schema_tables() -> None:
    """Fail fast if reviewed production migrations are absent.

    This is intentionally read-only. It catches an incomplete migration before
    the API is marked ready, while avoiding normal-boot DDL on constrained
    production instances.
    """

    expected = set(Base.metadata.tables)
    existing = set(inspect(_engine).get_table_names())
    missing = sorted(expected - existing)
    if missing:
        raise RuntimeError(
            "database schema verification failed; apply the reviewed migrations "
            f"before starting the API (missing tables: {', '.join(missing)})"
        )


def init_db() -> bool:
    """Prepare the database and return whether startup DDL was applied.

    The FastAPI lifespan always verifies the configured database is reachable.
    Schema mutation is limited to SQLite by default; migration-managed Postgres
    starts perform only the bounded readiness query.
    """

    from pathlib import Path

    if _db_url.startswith("sqlite"):
        path_str = _db_url.replace("sqlite:////", "/").replace("sqlite:///", "")
        if path_str and not path_str.startswith(":memory:"):
            Path(path_str).parent.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    should_bootstrap = should_bootstrap_schema(
        mode=settings.db_schema_bootstrap_mode,
        dialect_name=_engine.dialect.name,
    )
    if should_bootstrap:
        Base.metadata.create_all(_engine, checkfirst=True)
        _ensure_day28_outbox_columns()
        _ensure_supplier_auth_pin_nullable_sqlite()
        _ensure_product_composite_key_sqlite()
        _ensure_tenant_google_sheets_columns_sqlite()
        _ensure_tenant_data_retention_columns_sqlite()
        log.info(
            "db.schema_bootstrap_applied mode=%s dialect=%s",
            settings.db_schema_bootstrap_mode,
            _engine.dialect.name,
        )
        return True

    # Migration-managed PostgreSQL still fails fast on a broken DATABASE_URL,
    # without issuing table DDL on the request-readiness critical path. In auto
    # mode it additionally verifies every ORM-mapped table before Render routes
    # traffic to the newly woken instance.
    with _engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    if settings.db_schema_bootstrap_mode == "auto":
        verify_schema_tables()
        log.info("db.schema_verified dialect=%s", _engine.dialect.name)
    else:
        log.info(
            "db.schema_bootstrap_skipped mode=%s dialect=%s",
            settings.db_schema_bootstrap_mode,
            _engine.dialect.name,
        )
    return False


def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def async_session_scope() -> AsyncIterator[AsyncSession]:
    db = AsyncSessionLocal()
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


def reset_db() -> None:
    """Drop & recreate all tables — used in tests and seed-from-scratch."""
    _engine.dispose()
    Base.metadata.drop_all(_engine, checkfirst=True)
    Base.metadata.create_all(_engine, checkfirst=True)
