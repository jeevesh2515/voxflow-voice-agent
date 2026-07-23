"""FastAPI app entrypoint."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .config import get_settings
from .db import init_db
from .llm import get_llm
from .llm.base import ChatTurn
from .logging import get_logger, setup_logging
from .routes import data as data_routes
from .routes import ws as ws_routes
from .routes.ws import get_pipeline
from .schemas import ChatMessage, ChatRequest, ChatResponse
from .voice.tts import TextToSpeech


setup_logging()
log = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="VoxFlow Voice Agent",
        version="0.1.0",
        description="Voice operations, automated. Hindi + English supplier call agent.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        log.info("api.startup", provider=settings.llm_provider, model=getattr(settings, f"{settings.llm_provider}_model", ""))

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "service": "VoxFlow Voice Agent",
            "version": "0.1.0",
            "docs": "/docs",
            "dashboard": "see apps/web",
        }

    # Mount routers
    app.include_router(data_routes.router, prefix="/api", tags=["data"])
    app.include_router(ws_routes.router, tags=["ws"])

    # ----- LLM test endpoint (POST /chat) -----
    @app.post("/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest) -> ChatResponse:
        llm = get_llm()
        msgs = [
            ChatTurn(
                role=m.role,
                content=m.content,
                name=m.name,
                tool_call_id=m.tool_call_id,
                tool_calls=m.tool_calls,
            )
            for m in req.messages
        ]
        resp = await llm.chat(
            msgs,
            tools=req.tools,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        return ChatResponse(
            content=resp.content,
            tool_calls=resp.tool_calls,
            finish_reason=resp.finish_reason,
            provider=resp.provider,
            model=resp.model,
        )

    # ----- TTS test endpoint (POST /tts) -----
    class TTSRequest(BaseModel):
        text: str
        lang: str | None = None

    @app.post("/tts")
    async def tts(req: TTSRequest) -> StreamingResponse:
        if not req.text.strip():
            raise HTTPException(status_code=400, detail="empty_text")
        synth = TextToSpeech()
        res = await synth.synth(req.text, lang_hint=req.lang)
        return StreamingResponse(iter([res.audio_bytes]), media_type=res.mime)

    # ----- Quick "agent run" endpoint (text-in/text-out) -----
    class AgentRunRequest(BaseModel):
        text: str
        caller_phone: str = ""
        caller_name: str = ""
        language: str | None = None

    @app.post("/agent/run")
    async def agent_run(req: AgentRunRequest) -> dict[str, Any]:
        pipeline = get_pipeline()
        session = pipeline.start_session(
            caller_phone=req.caller_phone,
            caller_name=req.caller_name,
            language=req.language,
        )
        from .schemas import CallTurn
        from .agent.runner import AgentRunner

        session.transcript.append(CallTurn(role="caller", text=req.text, at=datetime.now(timezone.utc)))
        runner = AgentRunner()
        result = await runner.handle_turn(session=session, user_text=req.text)
        session.transcript.append(CallTurn(role="agent", text=result.reply, at=datetime.now(timezone.utc)))
        for a in result.actions:
            session.actions.append(a)
        # Persist immediately (don't wait for end_session)
        pipeline._persist(session)
        pipeline._sessions.pop(session.call_id, None)
        return {
            "call_id": session.call_id,
            "reply": result.reply,
            "actions": result.actions,
            "language": session.language,
        }

    return app


app = create_app()
