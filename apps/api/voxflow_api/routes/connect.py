"""Amazon Connect AWS Lambda integration routes.

Provides REST endpoints called by the AWS Lambda bridge during an active
Amazon Connect Contact Flow:
  - POST /api/connect/turn : Execute an agent turn given transcribed caller speech
  - POST /api/connect/end  : Persist call outcome to DB & Google Sheets when disconnected
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from ..agent.runner import AgentRunner
from ..config import get_settings
from ..db import TenantPhoneNumber, async_session_scope
from ..logging import get_logger
from ..schemas import CallTurn
from ..telephony.registry import get_telephony_provider
from ..voice.pipeline import CallSession
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
    session.transcript.append(CallTurn(role="caller", text=user_text, at=datetime.now(timezone.utc)))

    runner = AgentRunner()
    agent_result = await runner.handle_turn(session=session, user_text=user_text)

    session.transcript.append(CallTurn(role="agent", text=agent_result.reply, at=datetime.now(timezone.utc)))
    for a in agent_result.actions:
        session.actions.append(a)
        if a.get("name") == "escalate_to_human":
            session.escalated = True

    should_end = session.resolution_status != "" or session.outcome not in ("in_progress", "")

    log.info(
        "connect.turn_completed",
        contact_id=req.contact_id,
        caller=user_text,
        agent=agent_result.reply,
        escalated=session.escalated,
    )

    return ConnectTurnResponse(
        contact_id=req.contact_id,
        agent_reply=agent_result.reply,
        language=session.language,
        escalate=session.escalated,
        end_call=should_end,
        actions=agent_result.actions,
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
