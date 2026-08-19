"""FastAPI app entrypoint."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .auth import AuthMiddleware
from .config import get_settings
from .db import init_db
from .integrations.gsheets import get_sheets_client
from .llm import get_llm
from .llm.base import ChatTurn
from .logging import get_logger, setup_logging
from .routes import admin as admin_routes
from .routes import campaigns as campaign_routes
from .routes import data as data_routes
from .routes import twilio as twilio_routes
from .routes import ws as ws_routes
from .routes.ws import get_pipeline
from .schemas import ChatRequest, ChatResponse


setup_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # 1. Ensure persistent data directories exist
    data_dir = settings.resolved_data_dir
    for sub in ("sessions", "sheets_queue", "logs", "backups"):
        os.makedirs(os.path.join(data_dir, sub), exist_ok=True)

    # 2. Initialize database schema
    init_db()

    # 3. Recover orphaned sessions from disk (crash recovery)
    pipeline = get_pipeline()
    recovered = await pipeline.recover_orphaned_sessions()
    if recovered > 0:
        log.info("api.sessions_recovered", count=recovered)

    # 4. Start background worker for Google Sheets retry queue
    async def _sheets_retry_worker():
        sheets = get_sheets_client()
        while True:
            try:
                synced = await sheets.process_retry_queue()
                if synced > 0:
                    log.info("api.sheets_queue_processed", synced_count=synced)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning("api.sheets_queue_worker_error", error=str(e))
            await asyncio.sleep(settings.sheets_retry_interval)

    retry_task = asyncio.create_task(_sheets_retry_worker())

    # 5. Start background worker for Email Summarizer Agent (runs 3x daily / interval)
    async def _email_summarizer_worker():
        if not settings.email_summarizer_enabled:
            return
        # small delay on startup before first check
        await asyncio.sleep(10)
        from .tasks.email_summarizer import EmailSummarizerAgent
        agent = EmailSummarizerAgent(tenant_id=settings.default_tenant_id)
        while True:
            try:
                res = await agent.run_sync_cycle(limit=15)
                if res.get("processed_count", 0) > 0:
                    log.info("api.email_summarizer_scheduled_run", processed=res["processed_count"], synced=res["sheets_synced_count"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning("api.email_summarizer_worker_error", error=str(e))
            await asyncio.sleep(settings.email_summarizer_interval_seconds)

    email_task = asyncio.create_task(_email_summarizer_worker())

    log.info(
        "api.startup",
        provider=settings.llm_provider,
        model=getattr(settings, f"{settings.llm_provider}_model", ""),
        data_dir=settings.data_dir,
    )

    yield

    # Shutdown
    retry_task.cancel()
    email_task.cancel()
    try:
        await retry_task
    except asyncio.CancelledError:
        pass
    try:
        await email_task
    except asyncio.CancelledError:
        pass
    log.info("api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="VoxFlow Voice Agent",
        version="0.1.0",
        description="Voice operations, automated. Hindi + English supplier call agent.",
        lifespan=lifespan,
    )

    app.add_middleware(AuthMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.api_route("/", methods=["GET", "HEAD"])
    def root() -> dict[str, Any]:
        return {
            "service": "VoxFlow Voice Agent",
            "version": "0.1.0",
            "docs": "/docs",
            "dashboard": "see apps/web",
        }

    # Mount routers
    app.include_router(data_routes.router, prefix="/api", tags=["data"])
    app.include_router(admin_routes.router, prefix="/api/admin", tags=["admin"])
    app.include_router(campaign_routes.router)
    app.include_router(ws_routes.router, tags=["ws"])
    app.include_router(twilio_routes.router)

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
        from .voice.tts import TextToSpeech
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
        await pipeline._persist(session)
        pipeline._sessions.pop(session.call_id, None)
        return {
            "call_id": session.call_id,
            "reply": result.reply,
            "actions": result.actions,
            "language": session.language,
        }

    return app


app = create_app()
