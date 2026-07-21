"""Pydantic schemas for the REST + WebSocket API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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

    class Config:
        from_attributes = True


# ---------- Products & Stock ----------


class StockItem(BaseModel):
    sku: str
    name: str
    warehouse: str
    quantity: int
    pack_size: str
    mrp_inr: float

    class Config:
        from_attributes = True


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
