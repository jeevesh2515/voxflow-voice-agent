"""SQLite (dev) / Postgres (prod) data layer.

Both sync and async engines — sync for REST routes (FastAPI runs them in a
thread pool), async for the agent tool functions that run inside async handlers.

Single declarative base — schema created via `Base.metadata.create_all`.
Supports multi-tenant isolation via `tenant_id` foreign keys.
"""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from typing import AsyncIterator, Iterator

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from .config import get_settings


_settings = get_settings()

# Sync engine — for REST routes, CLI scripts
_engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {},
    echo=False,
    future=True,
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Async engine — for agent tool functions inside async handlers
def _async_db_url(url: str) -> str:
    if url.startswith("sqlite"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _pooled_url(url: str) -> str:
    switch = _settings.supabase_use_pooler
    if not switch:
        return url
    return url.replace(":5432/", ":6543/").replace(
        ".supabase.co", ".pooler.supabase.co"
    )

_async_engine = create_async_engine(
    _async_db_url(_pooled_url(_settings.database_url)),
    echo=False,
    future=True,
)
AsyncSessionLocal = async_sessionmaker(bind=_async_engine, autoflush=False, expire_on_commit=False)


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
    status: Mapped[str] = mapped_column(String(32), default="sent")  # sent | failed
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------- Helpers ----------


def init_db() -> None:
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
