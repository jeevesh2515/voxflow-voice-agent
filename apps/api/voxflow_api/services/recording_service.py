"""Server-side persistence for Connect call recordings + IVR consent evidence.

Pairs with deploy/aws/s3_recordings_handler.py and the UK contact flow
(connect-contact-flow-uk.json). The contact flow writes the contact attributes
``consent_granted`` / ``consent_recorded``; the S3 handler forwards them
here after the recording lands in the Connect bucket.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from ..db import Call, RecipientCampaignPreference, async_session_scope
from ..logging import get_logger

log = get_logger(__name__)


def build_consent_evidence(
    *,
    region: str,
    instance_id: str,
    contact_id: str,
    consent_granted: bool,
    consent_recorded: bool,
    ts: datetime,
) -> str:
    """Immutable evidence string for the ICO/GDPR audit trail."""
    state = "granted" if consent_granted else "denied"
    recorded = "yes" if consent_recorded else "no"
    return (
        f"connect:{region}:{instance_id}:{contact_id}:"
        f"consent={state}:recorded={recorded}:at={ts.isoformat()}"
    )


async def persist_recording_and_consent(payload: dict[str, Any]) -> dict[str, Any]:
    contact_id = (payload.get("contact_id") or "").strip()
    s3_key = (payload.get("s3_key") or "").strip()
    bucket = (payload.get("bucket") or "").strip()
    recording_url = (payload.get("recording_url") or "").strip()
    if not recording_url and bucket and s3_key:
        recording_url = f"s3://{bucket}/{s3_key}"

    consent_granted = bool(payload.get("consent_granted"))
    consent_recorded = bool(payload.get("consent_recorded"))
    region = payload.get("region") or "eu-west-2"
    instance_id = payload.get("instance_id") or ""

    if not contact_id or not s3_key:
        raise ValueError("contact_id and s3_key are required")

    if not consent_recorded:
        # No IVR consent recorded -> a recording should not exist; log and skip.
        log.warning("connect.recording_without_consent", contact_id=contact_id)
        return {"persisted": True, "reason": "consent_not_recorded", "evidence_ref": ""}

    now = datetime.now(timezone.utc)
    evidence_ref = build_consent_evidence(
        region=region,
        instance_id=instance_id,
        contact_id=contact_id,
        consent_granted=consent_granted,
        consent_recorded=consent_recorded,
        ts=now,
    )

    async with async_session_scope() as db:
        call = await db.get(Call, contact_id)
        if call is None:
            log.warning("connect.recording_call_not_found", contact_id=contact_id)
            return {"persisted": False, "reason": "call_not_found", "evidence_ref": ""}

        if call.recording_url and call.recording_url == recording_url:
            return {
                "persisted": True,
                "reason": "already_persisted",
                "evidence_ref": call.consent_evidence_ref,
            }

        call.recording_url = recording_url
        call.recording_s3_key = s3_key
        call.consent_granted = 1 if consent_granted else 0
        call.consent_recorded_at = now
        call.consent_evidence_ref = evidence_ref

        recipient_phone = (call.caller_phone or "").strip()
        if recipient_phone:
            prefs = await db.execute(
                select(RecipientCampaignPreference).where(
                    RecipientCampaignPreference.tenant_id == call.tenant_id,
                    RecipientCampaignPreference.recipient_phone == recipient_phone,
                )
            )
            pref = prefs.scalar_one_or_none()
            if pref is None:
                db.add(
                    RecipientCampaignPreference(
                        id=f"rcp-{uuid.uuid4().hex[:20]}",
                        tenant_id=call.tenant_id,
                        recipient_phone=recipient_phone,
                        consent_status="granted" if consent_granted else "withdrawn",
                        consent_purpose="inbound_call_recording",
                        opted_out=0 if consent_granted else 1,
                        source="connect_ivr_consent",
                    )
                )
            else:
                pref.consent_status = "granted" if consent_granted else "withdrawn"
                pref.consent_purpose = "inbound_call_recording"
                pref.opted_out = 0 if consent_granted else 1
                pref.source = "connect_ivr_consent"
                pref.updated_at = now

        log.info(
            "connect.recording_persisted",
            contact_id=contact_id,
            tenant_id=call.tenant_id,
            consent_granted=consent_granted,
        )
        return {"persisted": True, "reason": "ok", "evidence_ref": evidence_ref}
