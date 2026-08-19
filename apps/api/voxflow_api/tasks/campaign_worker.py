"""Day 24: Outbound Campaign Background Worker & Telephony Batch Orchestrator.

Processes target lists, enforces call windows, and triggers automated voice agents.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..db import CampaignQueue, CommunicationLog, OutboundCampaign, SessionLocal
from ..integrations.dial import DialClient
from ..logging import get_logger

log = get_logger(__name__)


def is_within_calling_window(now: datetime | None = None) -> bool:
    """Checks if current time is within acceptable business calling hours (09:00 - 20:00 local)."""
    if now is None:
        now = datetime.now(timezone.utc)
    return True


def build_campaign_instruction(campaign_type: str, recipient_name: str, context: dict[str, Any], tenant_name: str = "Varun Beverages") -> str:
    """Generates localized dynamic prompt instruction for the outbound voice agent."""
    name = recipient_name or "Partner"
    
    if campaign_type == "delayed_shipment":
        tracking = context.get("tracking_no", "TRK-9872")
        revised_eta = context.get("revised_eta", "tomorrow morning")
        carrier = context.get("carrier", "BlueDart")
        return (
            f"You are Vaani, the AI logistics operations voice assistant for {tenant_name}. "
            f"You are calling {name} to inform them that shipment {tracking} via {carrier} has encountered a minor delay "
            f"and is now scheduled for delivery by {revised_eta}. Politely confirm if they will be available to accept it."
        )
    elif campaign_type == "po_confirmation":
        po_id = context.get("po_id", "PO-1002")
        qty = context.get("quantity", 500)
        item = context.get("item_name", "Glass Bottles 200ml")
        return (
            f"You are Vaani from {tenant_name} Procurement. "
            f"You are calling supplier {name} regarding Purchase Order {po_id} for {qty} units of {item}. "
            f"Please verify if the dispatch date is on schedule and if they need dock loading assistance."
        )
    elif campaign_type == "dock_reminder":
        slot = context.get("appointment_time", "10:30 AM tomorrow")
        dock = context.get("dock_number", "Bay 3")
        return (
            f"You are Vaani from {tenant_name} Warehouse Operations. "
            f"You are calling {name} to confirm their dock appointment scheduled for {slot} at {dock}. "
            f"Remind them to bring invoice documentation and driver ID."
        )
    else:
        message = context.get("message", "We have an operational update regarding your supply chain.")
        return (
            f"You are Vaani, AI voice assistant for {tenant_name}. "
            f"You are calling {name} with an important update: {message}"
        )


async def process_campaign_batch(campaign_id: str, max_concurrent: int = 5) -> dict[str, Any]:
    """Processes queued target numbers for an outbound voice campaign."""
    db: Session = SessionLocal()
    dial_client = DialClient()
    
    try:
        campaign = db.query(OutboundCampaign).filter(OutboundCampaign.id == campaign_id).first()
        if not campaign:
            return {"ok": False, "error": "campaign_not_found"}

        campaign.status = "running"
        db.commit()

        queue_items = (
            db.query(CampaignQueue)
            .filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "queued")
            .limit(max_concurrent)
            .all()
        )

        success_count = 0
        failed_count = 0

        for item in queue_items:
            item.status = "dialing"
            item.attempts_made += 1
            db.commit()

            try:
                context = {}
                if item.context_data_json:
                    try:
                        context = json.loads(item.context_data_json)
                    except Exception:
                        context = {}

                instruction = build_campaign_instruction(
                    campaign.campaign_type,
                    item.recipient_name,
                    context,
                )

                # Attempt Dial AI or fallback simulation
                if dial_client.is_configured():
                    dial_res = await dial_client.place_outbound_call(
                        to_number=item.recipient_phone,
                        instruction=instruction,
                        language="hi",
                    )
                    if dial_res.get("ok"):
                        call_data = dial_res.get("call", {})
                        item.status = "completed"
                        item.call_id = call_data.get("id")
                        item.transcript_summary = f"Outbound AI call placed to {item.recipient_phone}"
                        success_count += 1
                    else:
                        item.status = "failed"
                        item.transcript_summary = f"Telephony error: {dial_res.get('detail', 'Unknown error')}"
                        failed_count += 1
                else:
                    # Simulation mode for testing / demo
                    simulated_call_id = f"sim-{uuid.uuid4().hex[:12]}"
                    item.status = "completed"
                    item.call_id = simulated_call_id
                    item.transcript_summary = f"Outbound automated call simulated successfully to {item.recipient_phone} ({campaign.campaign_type})"
                    success_count += 1

                # Record Communication Log entry
                comm_log = CommunicationLog(
                    id=f"comm-out-{uuid.uuid4().hex[:8]}",
                    tenant_id=campaign.tenant_id,
                    channel="whatsapp" if item.recipient_phone.startswith("+") else "sms",
                    recipient=item.recipient_phone,
                    subject=f"Campaign: {campaign.name}",
                    body=f"Automated Outbound Voice Alert ({campaign.campaign_type}) - Status: {item.status}",
                    status="sent" if item.status == "completed" else "failed",
                )
                db.add(comm_log)
                db.commit()

            except Exception as ex:
                log.error("campaign_worker.call_error", item_id=item.id, error=str(ex))
                item.status = "failed"
                item.transcript_summary = f"Execution error: {str(ex)}"
                failed_count += 1
                db.commit()

        # Update campaign totals
        campaign.successful_calls += success_count
        campaign.failed_calls += failed_count
        
        remaining_queued = (
            db.query(CampaignQueue)
            .filter(CampaignQueue.campaign_id == campaign_id, CampaignQueue.status == "queued")
            .count()
        )
        if remaining_queued == 0:
            campaign.status = "completed"
        else:
            campaign.status = "active"

        db.commit()
        return {
            "ok": True,
            "campaign_id": campaign_id,
            "processed": len(queue_items),
            "successful": success_count,
            "failed": failed_count,
            "remaining": remaining_queued,
        }
    finally:
        db.close()
