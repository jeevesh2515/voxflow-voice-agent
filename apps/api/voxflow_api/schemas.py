"""Pydantic schemas for the REST + WebSocket API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------- Suppliers ----------


class SupplierOut(BaseModel):
    id: str
    name: str
    phone: str
    city: str
    state: str
    pincode: str
    contact_person: str
    gstin: str
    auth_pin: str = "1234"

    model_config = ConfigDict(from_attributes=True)


class SupplierCreate(BaseModel):
    name: str
    phone: str
    city: str = "Gurgaon"
    state: str = "Haryana"
    pincode: str = "122001"
    contact_person: str = ""
    gstin: str = ""
    auth_pin: str = "1234"


class AppointmentCreate(BaseModel):
    supplier_id: str | None = None
    datetime: str
    purpose: str = "Supplier Operations & Delivery Audit"


class CommunicationCreate(BaseModel):
    channel: Literal["sms", "whatsapp", "email"] = "sms"
    recipient: str
    subject: str = ""
    body: str


# ---------- Products & Stock ----------


class StockItem(BaseModel):
    sku: str
    name: str
    warehouse: str
    quantity: int
    pack_size: str
    mrp_inr: float

    model_config = ConfigDict(from_attributes=True)


# ---------- Orders ----------


class OrderItemIn(BaseModel):
    sku: str
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    supplier_id: str
    items: list[OrderItemIn]
    notes: str = ""


class OrderOut(BaseModel):
    id: str
    supplier_id: str
    status: str
    items: list[OrderItemIn]
    total_qty: int
    notes: str
    created_at: datetime
    updated_at: datetime


# ---------- Shipments ----------


class ShipmentOut(BaseModel):
    id: str
    order_id: str
    status: str
    carrier: str
    tracking_no: str
    expected_delivery: datetime | None
    last_update: datetime
    history: list[dict[str, Any]] = []


# ---------- Calls ----------


CallOutcome = Literal["resolved", "escalated", "abandoned", "in_progress"]
CallIntent = Literal["order", "stock_check", "shipment_status", "general", "other"]


class CallTurn(BaseModel):
    role: Literal["caller", "agent"]
    text: str
    at: datetime


class CallAction(BaseModel):
    name: str
    args: dict[str, Any]
    result: dict[str, Any] | None = None
    at: datetime


class CallStartIn(BaseModel):
    caller_phone: str = ""
    caller_name: str = ""
    language: Literal["hi", "en"] | None = None


class CallOut(BaseModel):
    id: str
    started_at: datetime
    ended_at: datetime | None
    duration_sec: int
    supplier_id: str | None
    caller_phone: str
    caller_name: str
    language: str
    intent: str
    outcome: str
    escalated: bool
    transcript: list[CallTurn]
    actions: list[CallAction]
    # Structured call-outcome fields
    reason: str
    solution: str
    resolution_status: str
    satisfaction: str
    follow_up_required: bool
    staff_resolution: str
    staff_resolved_at: datetime | None
    sheet_synced: bool
    verified: bool
    recording_url: str | None = None


class ResolutionIn(BaseModel):
    staff_resolution: str


class OutboundCallIn(BaseModel):
    to_phone: str
    instruction: str
    voice_gender: str = "female"
    language: str | None = None
    max_duration_seconds: int | None = None


# ---------- LLM / Agent ----------


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None


class ChatResponse(BaseModel):
    content: str
    tool_calls: list[dict[str, Any]] = []
    finish_reason: str = "stop"
    provider: str
    model: str


# ---------- Workspace Provisioning ----------


class WorkspaceProvisionIn(BaseModel):
    tenant_id: str = Field(..., description="Unique slug for the workspace, e.g. acme-logistics")
    name: str = Field(..., description="Company display name")
    plan: str = "pro"
    admin_name: str = ""
    admin_email: str = ""
    phone_number: str | None = None
    default_language: str = "en"
    seed_starter_data: bool = True


class WorkspaceProvisionOut(BaseModel):
    ok: bool
    tenant_id: str
    name: str
    plan: str
    message: str
    stats: dict[str, int] = {}


# ---------- Company Data Ingestion (CSV) ----------


class CsvValidationIn(BaseModel):
    csv_text: str = Field(..., description="Raw CSV string content to validate")
    tenant_id: str | None = None


class CsvImportIn(BaseModel):
    csv_text: str = Field(..., description="Raw CSV string content to import")
    mode: Literal["upsert", "strict"] = "upsert"


class CsvValidationOut(BaseModel):
    entity: str
    total_rows: int
    valid_rows: int
    error_count: int
    errors: list[dict[str, Any]] = []
    preview: list[dict[str, Any]] = []
    headers: list[str] = []
    is_valid: bool


class CsvImportOut(BaseModel):
    success: bool
    entity: str
    tenant_id: str
    inserted: int
    updated: int
    total_processed: int
    message: str
    errors: list[dict[str, Any]] = []

