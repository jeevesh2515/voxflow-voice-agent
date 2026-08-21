"""Privacy lifecycle helpers for the controlled VoxFlow MVP.

All methods are database-only. They calculate redacted retention evidence and
record requests for human verification; none exports raw records, deletes data,
retrieves recordings, contacts providers, or dispatches a worker.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal
import uuid

from sqlalchemy.orm import Session

from .config import get_settings
from .db import Call, CommunicationLog, PrivacyRequest, TenantPrivacyPolicy
from .jobs.staging import durable_campaign_dry_run, durable_side_effects_dry_run


REQUEST_TYPES = frozenset({"access_export", "deletion", "demo_reset"})
REVIEW_STATUSES = frozenset({"human_verification_required", "approved_for_manual_export", "blocked", "cancelled"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def subject_reference_hash(subject_reference: str) -> str:
    """Hash a normalized subject reference without retaining the raw identifier."""

    return sha256(subject_reference.strip().lower().encode("utf-8")).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def get_or_create_policy(db: Session, tenant_id: str) -> TenantPrivacyPolicy:
    policy = db.get(TenantPrivacyPolicy, tenant_id)
    if policy is None:
        policy = TenantPrivacyPolicy(tenant_id=tenant_id)
        db.add(policy)
        db.flush()
    return policy


def privacy_policy_payload(policy: TenantPrivacyPolicy) -> dict[str, object]:
    return {
        "tenant_id": policy.tenant_id,
        "call_transcript_retention_days": policy.call_transcript_retention_days,
        "communication_retention_days": policy.communication_retention_days,
        "recording_retention_days": policy.recording_retention_days,
        "recording_retrieval_enabled": False,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


def retention_preview(db: Session, tenant_id: str) -> dict[str, object]:
    """Return aggregate retention eligibility with no row-level operational data."""

    now = _utcnow()
    policy = get_or_create_policy(db, tenant_id)
    transcript_cutoff = now - timedelta(days=policy.call_transcript_retention_days)
    communication_cutoff = now - timedelta(days=policy.communication_retention_days)
    calls = db.query(Call).filter(Call.tenant_id == tenant_id).all()
    communications = db.query(CommunicationLog).filter(CommunicationLog.tenant_id == tenant_id).all()
    due_transcripts = sum(
        1
        for call in calls
        if bool(call.transcript_json and call.transcript_json != "[]")
        and (_as_utc(call.started_at) or now) <= transcript_cutoff
    )
    due_communications = sum(
        1
        for communication in communications
        if (_as_utc(communication.timestamp) or now) <= communication_cutoff
    )
    recording_references = sum(1 for call in calls if bool(call.recording_url))
    return {
        "tenant_id": tenant_id,
        "policy": privacy_policy_payload(policy),
        "preview": {
            "call_records_scanned": len(calls),
            "transcript_records_eligible_for_review": due_transcripts,
            "communication_records_scanned": len(communications),
            "communication_records_eligible_for_review": due_communications,
            "recording_reference_count": recording_references,
            "recording_retrieval_enabled": False,
        },
        "execution": {
            "mode": "preview_only",
            "purge_job_enqueued": False,
            "provider_accessed": False,
            "raw_record_exported": False,
        },
        "required_gate": "human_review_and_tenant_authorization_required_before_any_manual_data_action",
    }


def request_payload(request: PrivacyRequest) -> dict[str, object]:
    return {
        "id": request.id,
        "tenant_id": request.tenant_id,
        "request_type": request.request_type,
        "status": request.status,
        "requested_by": request.requested_by,
        "review_note": request.review_note,
        "created_at": request.created_at.isoformat() if request.created_at else None,
        "reviewed_at": request.reviewed_at.isoformat() if request.reviewed_at else None,
        "reviewed_by": request.reviewed_by,
    }


def create_privacy_request(
    db: Session,
    *,
    tenant_id: str,
    request_type: Literal["access_export", "deletion", "demo_reset"],
    subject_reference: str,
    requested_by: str,
) -> PrivacyRequest:
    if request_type not in REQUEST_TYPES:
        raise ValueError("unsupported privacy request type")
    request = PrivacyRequest(
        id=f"prv-{uuid.uuid4().hex[:20]}",
        tenant_id=tenant_id,
        request_type=request_type,
        subject_hash=subject_reference_hash(subject_reference) if subject_reference else "",
        status="pending_human_review",
        requested_by=requested_by,
    )
    db.add(request)
    db.flush()
    return request


def review_privacy_request(
    request: PrivacyRequest,
    *,
    reviewed_by: str,
    status: Literal["human_verification_required", "approved_for_manual_export", "blocked", "cancelled"],
    review_note: str,
) -> PrivacyRequest:
    if status not in REVIEW_STATUSES:
        raise ValueError("unsupported privacy request review status")
    request.status = status
    request.reviewed_by = reviewed_by
    request.reviewed_at = _utcnow()
    request.review_note = review_note.strip()[:512]
    return request


def demo_reset_preview(tenant_id: str) -> dict[str, object]:
    """Report immutable blocked gates for a sanitized demonstration reset."""

    settings = get_settings()
    is_fixed_demo_tenant = tenant_id == settings.demo_tenant_id
    gates = [
        {
            "code": "fixed_demo_tenant_required",
            "met": is_fixed_demo_tenant,
            "detail": "Only the configured demonstration tenant is eligible for a sanitized reset request.",
        },
        {
            "code": "campaign_worker_disabled",
            "met": not settings.durable_campaign_worker_enabled and durable_campaign_dry_run(),
            "detail": "The campaign worker must remain disabled and dry-run.",
        },
        {
            "code": "side_effect_worker_disabled",
            "met": not settings.durable_side_effects_worker_enabled and durable_side_effects_dry_run(),
            "detail": "The side-effect worker must remain disabled and dry-run.",
        },
        {
            "code": "manual_approval_required",
            "met": False,
            "detail": "A reset is never executed from the browser; an authorized human must review a separate change record.",
        },
    ]
    return {
        "tenant_id": tenant_id,
        "operation": "sanitized_demo_reset",
        "execution": "blocked_preview_only",
        "eligible_for_request": is_fixed_demo_tenant,
        "all_gates_met": all(bool(gate["met"]) for gate in gates),
        "gates": gates,
        "provider_accessed": False,
        "data_deleted": False,
    }
