"""FastAPI app entrypoint."""

from __future__ import annotations

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
from .db import close_db_engines, init_db
from .llm import get_llm
from .llm.base import ChatTurn
from .logging import get_logger, setup_logging
from .monitoring import init_error_monitoring
from .routes import admin as admin_routes
from .routes import analytics as analytics_routes
from .routes import campaign_policies as campaign_policy_routes
from .routes import campaigns as campaign_routes
from .routes import data as data_routes
from .routes import design_partner as design_partner_routes
from .routes import dial_callbacks as dial_callback_routes
from .routes import jobs as job_routes
from .routes import memberships as membership_routes
from .routes import provider_callbacks as provider_callback_routes
from .routes import pilot_operations as pilot_operations_routes
from .routes import pilot_readiness as pilot_readiness_routes
from .routes import privacy as privacy_routes
from .routes import public_auth as public_auth_routes
from .routes import reliability as reliability_routes
from .routes import connect as connect_routes
from .routes import ws as ws_routes
from .routes.ws import get_pipeline
from .schemas import ChatRequest, ChatResponse


setup_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # 1. Ensure persistent data directories exist. Day 34 removed the
    # process-local Sheets retry queue; durable jobs and the database own retry
    # state instead of an API-instance filesystem directory.
    data_dir = settings.resolved_data_dir
    for sub in ("sessions", "logs", "backups"):
        os.makedirs(os.path.join(data_dir, sub), exist_ok=True)

    # 2. Initialize database schema
    init_db()

    # 3. Recover orphaned sessions from disk (crash recovery)
    pipeline = get_pipeline()
    recovered = await pipeline.recover_orphaned_sessions()
    if recovered > 0:
        log.info("api.sessions_recovered", count=recovered)

    # 4. Day 34 deliberately starts no side-effect worker here. Sheets retries,
    # email scans, CRM sync, notifications, and recording retrieval are typed
    # JobRun rows claimed only by the separately deployed, feature-gated worker.

    log.info(
        "api.startup",
        provider=settings.llm_provider,
        model=getattr(settings, f"{settings.llm_provider}_model", ""),
        data_dir=settings.data_dir,
    )

    yield

    # Shutdown
    await close_db_engines()
    log.info("api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    init_error_monitoring()
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
    app.include_router(analytics_routes.router)
    app.include_router(campaign_routes.router)
    app.include_router(campaign_policy_routes.router)
    app.include_router(job_routes.router)
    app.include_router(design_partner_routes.router)
    app.include_router(membership_routes.router)
    app.include_router(pilot_readiness_routes.router)
    app.include_router(privacy_routes.router)
    app.include_router(public_auth_routes.router)
    app.include_router(pilot_operations_routes.router)
    app.include_router(reliability_routes.router)
    app.include_router(provider_callback_routes.router)
    app.include_router(dial_callback_routes.router)
    app.include_router(ws_routes.router, tags=["ws"])
    app.include_router(connect_routes.router)

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
