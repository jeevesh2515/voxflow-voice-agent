"""Amazon Connect AWS Lambda integration routes.

Provides REST endpoints called by the AWS Lambda bridge during an active
Amazon Connect Contact Flow:
  - POST /api/connect/turn : Execute an agent turn given transcribed caller speech
  - POST /api/connect/end  : Persist call outcome to DB & Google Sheets when disconnected
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..agent.runner import AgentRunner
from ..config import get_settings
from ..db import TenantPhoneNumber, async_session_scope
from ..logging import get_logger
from ..schemas import CallTurn
from ..telephony.registry import get_telephony_provider
from .ws import get_pipeline

log = get_logger(__name__)
router = APIRouter(prefix="/api/connect", tags=["amazon_connect"])


class ConnectTurnRequest(BaseModel):
    contact_id: str
    customer_phone: str = ""
    system_phone: str = ""
    user_text: str
    language: Optional[str] = None


class ConnectTurnResponse(BaseModel):
    contact_id: str
    agent_reply: str
    language: str
    escalate: bool = False
    end_call: bool = False
    actions: list[dict[str, Any]] = []
    latency_ms: Optional[float] = None


class ConnectEndRequest(BaseModel):
    contact_id: str
    outcome: str = "resolved"


async def _resolve_connect_tenant(system_phone: str) -> str:
    s = get_settings()
    if not system_phone:
        return s.default_tenant_id

    from sqlalchemy import select

    try:
        async with async_session_scope() as db:
            row = (
                await db.execute(
                    select(TenantPhoneNumber).where(
                        TenantPhoneNumber.phone_number == system_phone,
                        TenantPhoneNumber.active == 1,
                    )
                )
            ).scalars().first()
            if row:
                return row.tenant_id
    except Exception as e:
        log.error("connect.tenant_lookup_failed", to=system_phone, error=str(e))

    return s.default_tenant_id


@router.post("/turn", response_model=ConnectTurnResponse)
async def connect_turn(
    req: ConnectTurnRequest,
    request: Request,
) -> ConnectTurnResponse:
    """Execute one conversational turn from Amazon Connect."""
    import time
    start_time = time.perf_counter()

    provider = get_telephony_provider("connect")
    form_dict = req.model_dump()
    if not provider.validate_webhook(request, form_dict, "/api/connect/turn"):
        log.warning("connect.invalid_signature", contact_id=req.contact_id)
        raise HTTPException(status_code=403, detail="invalid_signature")

    pipeline = get_pipeline()
    session = pipeline.get_session(req.contact_id)

    if session is None:
        tenant_id = await _resolve_connect_tenant(req.system_phone)
        session = pipeline.start_session(
            caller_phone=req.customer_phone,
            language=req.language or get_settings().tts_default_lang,
            tenant_id=tenant_id,
            call_id=req.contact_id,
        )

    user_text = req.user_text.strip()
    if not user_text:
        session.silence_count += 1
        is_hindi = session.language == "hi"
        if session.silence_count == 1:
            if len(session.transcript) <= 1:
                agent_reply = (
                    "नमस्ते, मैं वॉक्सफ़्लो वॉयस असिस्टेंट हूँ। मैं आज आपकी क्या सहायता कर सकता हूँ?"
                    if is_hindi
                    else "Hello, this is the VoxFlow voice assistant. How can I help you today?"
                )
            else:
                agent_reply = (
                    "क्या आप अभी भी वहाँ हैं? आप क्या जानना चाहते हैं?"
                    if is_hindi
                    else "Are you still there? What would you like to know?"
                )
            should_end = False
        elif session.silence_count == 2:
            agent_reply = (
                "मैं अभी भी यहीं हूँ। क्या आप स्टॉक या ऑर्डर की जानकारी चाहते हैं, या किसी सहयोगी से बात करना चाहेंगे?"
                if is_hindi
                else "I'm still here. How can I help with your stock or order inquiry, or would you like to speak to a colleague?"
            )
            should_end = False
        else:
            agent_reply = (
                "आपकी आवाज़ नहीं आ रही है, इसलिए मैं अभी कॉल समाप्त कर रहा हूँ। कृपया बाद में फिर कॉल करें।"
                if is_hindi
                else "I haven't heard anything from you, so I'll end the call for now. Please feel free to call back."
            )
            should_end = True
            session.resolution_status = "abandoned"
            session.outcome = "abandoned"

        actions: list[dict[str, Any]] = []
        session.transcript.append(CallTurn(role="caller", text="[silence]", at=datetime.now(timezone.utc)))
        session.transcript.append(CallTurn(role="agent", text=agent_reply, at=datetime.now(timezone.utc)))
    else:
        session.silence_count = 0
        session.transcript.append(CallTurn(role="caller", text=user_text, at=datetime.now(timezone.utc)))

        runner = AgentRunner()
        agent_result = await runner.handle_turn(session=session, user_text=user_text)
        agent_reply = agent_result.reply
        actions = agent_result.actions

        session.transcript.append(CallTurn(role="agent", text=agent_reply, at=datetime.now(timezone.utc)))
        for a in actions:
            session.actions.append(a)
            if a.get("name") == "escalate_to_human":
                session.escalated = True

        should_end = session.resolution_status != "" or session.outcome not in ("in_progress", "")

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    session.turn_latencies.append(latency_ms)

    log.info(
        "connect.turn_completed",
        contact_id=req.contact_id,
        caller=user_text or "[silence]",
        silence_count=session.silence_count,
        agent=agent_reply,
        escalated=session.escalated,
        latency_ms=latency_ms,
    )

    return ConnectTurnResponse(
        contact_id=req.contact_id,
        agent_reply=agent_reply,
        language=session.language,
        escalate=session.escalated,
        end_call=should_end,
        actions=actions,
        latency_ms=latency_ms,
    )


@router.post("/end")
async def connect_end(
    req: ConnectEndRequest,
    request: Request,
) -> dict[str, Any]:
    """Finalize an Amazon Connect session upon call completion."""
    provider = get_telephony_provider("connect")
    if not provider.validate_webhook(request, req.model_dump(), "/api/connect/end"):
        raise HTTPException(status_code=403, detail="invalid_signature")

    pipeline = get_pipeline()
    session = await pipeline.end_session(req.contact_id, outcome=req.outcome)

    log.info("connect.call_ended", contact_id=req.contact_id, outcome=req.outcome)
    return {
        "ok": True,
        "contact_id": req.contact_id,
        "persisted": session is not None,
    }
