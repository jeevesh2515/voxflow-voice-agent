"""Day 24: Outbound Campaigns REST Router for autonomous voice operations."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import ROLE_OPERATOR, ROLE_OWNER, ROLE_VIEWER, require_tenant_role
from ..db import CampaignPolicyDecision, CampaignQueue, OutboundCampaign, get_session
from ..jobs.enqueue import enqueue_campaign_target
from ..jobs.staging import campaign_activation_mode
router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _authorize_tenant(request: Request, db: Session, tenant_id: str, *, write: bool = False) -> None:
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR} if write else {ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
        allow_demo=not write,
    )


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
    request: Request,
    tenant_id: str = Query("varun"),
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """List all outbound voice campaigns for an authorized tenant only."""
    _authorize_tenant(request, db, tenant_id)
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
    request: Request,
    tenant_id: str = Query("varun"),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Record durable campaign intent without dispatching a worker or provider.

    The campaign worker remains disabled and dry-run by configuration. This
    handler performs database-only staging; it never places a call, registers a
    callback, sends a message, or starts a background worker.
    """

    _authorize_tenant(request, db, tenant_id, write=True)
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
    return {
        "ok": True,
        "id": campaign_id,
        "name": campaign.name,
        "campaign_type": campaign.campaign_type,
        "status": campaign.status,
        "total_targets": len(req.targets),
        "execution_mode": campaign_activation_mode(),
        "message": "Campaign intent is database-staged only; worker and provider dispatch remain disabled.",
    }


@router.get("/{campaign_id}")
def get_campaign_detail(
    campaign_id: str,
    request: Request,
    tenant_id: str = Query("varun", min_length=1),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Retrieve tenant-owned campaign details, statistics, and progress."""
    _authorize_tenant(request, db, tenant_id)
    campaign = (
        db.query(OutboundCampaign)
        .filter(OutboundCampaign.id == campaign_id, OutboundCampaign.tenant_id == tenant_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    queue_stats = {
        "queued": db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "queued").count(),
        "dialing": db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "dialing").count(),
        "completed": db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "completed").count(),
        "failed": db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "failed").count(),
        "cancelled": db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "cancelled").count(),
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
def stage_campaign_run(
    campaign_id: str,
    request: Request,
    tenant_id: str = Query("varun"),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Change staged intent state without dispatching calls or starting work."""

    _authorize_tenant(request, db, tenant_id, write=True)
    campaign = (
        db.query(OutboundCampaign)
        .filter(OutboundCampaign.id == campaign_id, OutboundCampaign.tenant_id == tenant_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "draft":
        campaign.status = "active"
        db.commit()
    return {
        "ok": True,
        "id": campaign_id,
        "processed": 0,
        "successful": 0,
        "execution_mode": campaign_activation_mode(),
        "message": "Campaign intent is staged only; worker and provider dispatch remain disabled.",
    }


@router.get("/{campaign_id}/policy-decisions")
def get_campaign_policy_decisions(
    campaign_id: str,
    request: Request,
    tenant_id: str = Query("varun", min_length=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Return tenant-owned immutable policy decisions without provider payloads."""

    _authorize_tenant(request, db, tenant_id)
    campaign = (
        db.query(OutboundCampaign)
        .filter(OutboundCampaign.id == campaign_id, OutboundCampaign.tenant_id == tenant_id)
        .one_or_none()
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    rows = (
        db.query(CampaignPolicyDecision)
        .filter(
            CampaignPolicyDecision.tenant_id == tenant_id,
            CampaignPolicyDecision.campaign_id == campaign_id,
        )
        .order_by(CampaignPolicyDecision.created_at.desc(), CampaignPolicyDecision.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "job_id": row.job_id,
            "campaign_queue_id": row.campaign_queue_id,
            "decision": row.decision,
            "reason_code": row.reason_code,
            "next_eligible_at": row.next_eligible_at.isoformat() if row.next_eligible_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/{campaign_id}/queue")
def get_campaign_queue(
    campaign_id: str,
    request: Request,
    tenant_id: str = Query("varun", min_length=1),
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """List tenant-owned queue targets and individual call results for a campaign."""
    _authorize_tenant(request, db, tenant_id)
    campaign = (
        db.query(OutboundCampaign)
        .filter(OutboundCampaign.id == campaign_id, OutboundCampaign.tenant_id == tenant_id)
        .one_or_none()
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    items = (
        db.query(CampaignQueue)
        .filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.tenant_id == tenant_id)
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
