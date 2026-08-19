"""Day 24: Outbound Campaigns REST Router for autonomous voice operations."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import CampaignQueue, OutboundCampaign, get_session
from ..jobs.enqueue import enqueue_campaign_target
from ..logging import get_logger
from ..tasks.campaign_worker import process_campaign_batch

log = get_logger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class TargetItem(BaseModel):
    phone: str = Field(..., description="E.164 phone number")
    name: str = Field("", description="Recipient or supplier contact name")
    context: dict[str, Any] = Field(default_factory=dict, description="Contextual parameters like order_id, revised_eta")


class CreateCampaignRequest(BaseModel):
    name: str
    campaign_type: str = "delayed_shipment"  # delayed_shipment | po_confirmation | dock_reminder | generic
    targets: list[TargetItem] = Field(default_factory=list)
    auto_start: bool = False


@router.get("")
def list_campaigns(
    tenant_id: str = Query("varun"),
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """List all outbound voice campaigns for a tenant."""
    rows = (
        db.query(OutboundCampaign)
        .filter(OutboundCampaign.tenant_id == tenant_id)
        .order_by(OutboundCampaign.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "name": r.name,
            "campaign_type": r.campaign_type,
            "status": r.status,
            "total_targets": r.total_targets,
            "successful_calls": r.successful_calls,
            "failed_calls": r.failed_calls,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


@router.post("")
async def create_campaign(
    req: CreateCampaignRequest,
    tenant_id: str = Query("varun"),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Create a new outbound voice campaign and populate its call queue."""
    campaign_id = f"cmp-{uuid.uuid4().hex[:10]}"
    
    campaign = OutboundCampaign(
        id=campaign_id,
        tenant_id=tenant_id,
        name=req.name.strip(),
        campaign_type=req.campaign_type,
        status="active" if req.auto_start else "draft",
        total_targets=len(req.targets),
        successful_calls=0,
        failed_calls=0,
    )
    db.add(campaign)

    for target in req.targets:
        queue_item = CampaignQueue(
            id=f"cq-{uuid.uuid4().hex[:12]}",
            campaign_id=campaign_id,
            tenant_id=tenant_id,
            recipient_phone=target.phone.strip(),
            recipient_name=target.name.strip(),
            context_data_json=json.dumps(target.context),
            status="queued",
            attempts_made=0,
        )
        db.add(queue_item)
        enqueue_campaign_target(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            campaign_queue_id=queue_item.id,
        )

    db.commit()

    if req.auto_start and req.targets:
        # Run first batch immediately
        await process_campaign_batch(campaign_id, max_concurrent=len(req.targets))

    return {
        "ok": True,
        "id": campaign_id,
        "name": campaign.name,
        "campaign_type": campaign.campaign_type,
        "status": campaign.status,
        "total_targets": len(req.targets),
    }


@router.get("/{campaign_id}")
def get_campaign_detail(
    campaign_id: str,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Retrieve full details, statistics, and progress for a campaign."""
    campaign = db.query(OutboundCampaign).filter(OutboundCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    queue_stats = {
        "queued": db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "queued").count(),
        "dialing": db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "dialing").count(),
        "completed": db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "completed").count(),
        "failed": db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "failed").count(),
    }

    return {
        "id": campaign.id,
        "tenant_id": campaign.tenant_id,
        "name": campaign.name,
        "campaign_type": campaign.campaign_type,
        "status": campaign.status,
        "total_targets": campaign.total_targets,
        "successful_calls": campaign.successful_calls,
        "failed_calls": campaign.failed_calls,
        "queue_stats": queue_stats,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
    }


@router.post("/{campaign_id}/run")
async def run_campaign(
    campaign_id: str,
    max_concurrent: int = Query(5, ge=1, le=20),
) -> dict[str, Any]:
    """Trigger execution of queued calls for a campaign."""
    res = await process_campaign_batch(campaign_id, max_concurrent=max_concurrent)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Execution failed"))
    return res


@router.get("/{campaign_id}/queue")
def get_campaign_queue(
    campaign_id: str,
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """List queue targets and individual call results for a campaign."""
    items = (
        db.query(CampaignQueue)
        .filter(CampaignQueue.campaign_id == campaign_id)
        .order_by(CampaignQueue.updated_at.desc())
        .all()
    )
    return [
        {
            "id": it.id,
            "recipient_phone": it.recipient_phone,
            "recipient_name": it.recipient_name,
            "status": it.status,
            "attempts_made": it.attempts_made,
            "call_id": it.call_id,
            "transcript_summary": it.transcript_summary,
            "updated_at": it.updated_at.isoformat() if it.updated_at else None,
        }
        for it in items
    ]
