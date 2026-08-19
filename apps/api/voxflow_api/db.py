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
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
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
    default_language: Mapped[str] = mapped_column(String(8), default="hi")
    webhook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    plan: Mapped[str] = mapped_column(String(32), default="pro")
    total_minutes_used: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


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
    # Tier 2 PIN authentication for order creation and sensitive updates
    auth_pin: Mapped[str] = mapped_column(String(16), default="1234")
    # Which side of the trade this contact sits on.
    # customer = they buy from us | supplier = they sell to us | both
    contact_type: Mapped[str] = mapped_column(String(16), default="customer", index=True)
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="supplier", cascade="all,delete")


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(128))
    pack_size: Mapped[str] = mapped_column(String(64))
    mrp_inr: Mapped[float] = mapped_column(Float)


class Stock(Base):
    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True, default="varun")
    sku: Mapped[str] = mapped_column(String(64), ForeignKey("products.sku"), index=True)
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
    language: Mapped[str] = mapped_column(String(8), default="hi")
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
    # Whether this call's outcome row reached Google Sheets.
    sheet_synced: Mapped[int] = mapped_column(Integer, default=0)
    # Twilio call recording audio URL (if recorded)
    recording_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verified: Mapped[int] = mapped_column(Integer, default=0)


class TenantPhoneNumber(Base):
    """Maps an inbound Twilio number to the tenant that owns it.

    Without this, every inbound call falls through to the default tenant —
    which silently breaks multi-tenant isolation the moment a second
    customer is onboarded.
    """

    __tablename__ = "tenant_phone_numbers"

    phone_number: Mapped[str] = mapped_column(String(32), primary_key=True)  # E.164, e.g. +14155551234
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id"), index=True)
    label: Mapped[str] = mapped_column(String(128), default="")
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


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
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued | dialing | answered | no_answer | completed | failed
    attempts_made: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transcript_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ---------- Helpers ----------


def init_db() -> None:
    from pathlib import Path
    if _db_url.startswith("sqlite"):
        path_str = _db_url.replace("sqlite:////", "/").replace("sqlite:///", "")
        if path_str and not path_str.startswith(":memory:"):
            Path(path_str).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(_engine)


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
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)
