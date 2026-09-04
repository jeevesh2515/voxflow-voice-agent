"""POST /api/connect/recording - HMAC-signed ingest for Connect recordings.

Called by deploy/aws/s3_recordings_handler.py after Amazon Connect writes
a call recording to its S3 bucket.

Registration in main.py:
    from .routes import recording as recording_routes
    app.include_router(recording_routes.router)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..logging import get_logger
from ..services.recording_service import persist_recording_and_consent
from ..telephony.registry import get_telephony_provider

log = get_logger(__name__)

router = APIRouter(prefix="/api/connect", tags=["amazon_connect_recordings"])


class RecordingEvent(BaseModel):
    contact_id: str
    bucket: str = ""
    s3_key: str = ""
    recording_url: str = ""
    instance_id: str = ""
    region: str = "eu-west-2"
    consent_granted: bool = False
    consent_recorded: bool = False


@router.post("/recording")
async def connect_recording(req: RecordingEvent, request: Request) -> dict[str, Any]:
    provider = get_telephony_provider("connect")
    request.state.connect_raw_body = await request.body()
    if not provider.validate_webhook(request, req.model_dump(), "/api/connect/recording"):
        raise HTTPException(status_code=403, detail="invalid_signature")

    try:
        result = await persist_recording_and_consent(req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not result.get("persisted"):
        log.warning(
            "connect.recording_not_persisted",
            contact_id=req.contact_id,
            reason=result.get("reason"),
        )
        raise HTTPException(status_code=404, detail=result.get("reason", "call_not_found"))

    log.info(
        "connect.recording_ingested",
        contact_id=req.contact_id,
        consent_granted=req.consent_granted,
    )
    return {
        "ok": True,
        "contact_id": req.contact_id,
        "persisted": True,
        "evidence_ref": result.get("evidence_ref", ""),
    }
