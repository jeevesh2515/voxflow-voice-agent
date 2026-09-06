"""Retention purge — scrub expired transcripts/calls, idempotent, dry-run safe."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..db import Call, RetentionPurgeLog, Tenant
from ..logging import get_logger


log = get_logger(__name__)

# Signature of the recording-deletion seam: takes an s3:// URL, returns True
# when the stored object is gone. Tests inject a fake; production uses boto3.
RecordingDeleter = Callable[[str], bool]


def delete_recording_object(recording_url: str | None) -> bool:
    """Delete the stored recording object behind an ``s3://bucket/key`` URL.

    Clearing ``calls.recording_url`` alone only orphans the audio in the
    bucket — this removes the bytes. Never raises: a purge run must not die
    halfway because one object was already gone. Returns False for empty,
    non-S3, or unparsable URLs so callers can distinguish "nothing to delete"
    from "deleted".
    """

    if not recording_url or not recording_url.startswith("s3://"):
        return False
    parsed = urlparse(recording_url)
    bucket, key = parsed.netloc, parsed.path.lstrip("/")
    if not bucket or not key:
        return False
    try:
        import boto3

        boto3.client("s3").delete_object(Bucket=bucket, Key=key)
    except Exception as exc:  # already gone, no creds, no network — purge continues
        log.warning("retention.recording_delete_failed", bucket=bucket, error=str(exc)[:160])
        return False
    return True


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def run_retention_purge(
    db: Session,
    tenant_id: str | None = None,
    dry_run: bool = False,
    triggered_by_user_id: str | None = None,
    execution_type: str | None = None,
    recording_deleter: RecordingDeleter | None = None,
) -> dict[str, Any]:
    """Purge expired transcripts and anonymize expired call records.

    For each tenant:
    - transcript_retention_days: calls where started_at < now - transcript_retention_days => wipe transcript_json/reason/solution
    - call_retention_days: calls where started_at < now - call_retention_days => anonymize caller data + wipe transcript
    Writes immutable audit log (unless dry_run with zero counts? still logs for audit).
    """
    now = _utcnow()
    tenants = []
    if tenant_id:
        t = db.get(Tenant, tenant_id)
        if t:
            tenants = [t]
    else:
        tenants = db.query(Tenant).all()

    total_scanned = 0
    total_transcripts_purged = 0
    total_calls_anonymized = 0
    total_recordings_deleted = 0
    deleter = recording_deleter or delete_recording_object

    exec_type = execution_type or ("manual_trigger" if triggered_by_user_id else "automated_cron")

    per_tenant: list[tuple[str, dict[str, int]]] = []
    for tenant in tenants:
        transcript_days = getattr(tenant, "transcript_retention_days", 30) or 30
        call_days = getattr(tenant, "call_retention_days", 90) or 90
        transcript_cutoff = now - timedelta(days=transcript_days)
        call_cutoff = now - timedelta(days=call_days)

        # Per-tenant snapshot: a global run audits each tenant with its own
        # deltas, not the running cumulative totals.
        tenant_counts = {
            "scanned": 0,
            "anonymized": 0,
            "transcripts": 0,
            "recordings": 0,
        }

        calls = db.query(Call).filter(Call.tenant_id == tenant.id).all()
        total_scanned += len(calls)
        tenant_counts["scanned"] = len(calls)
        per_tenant.append((tenant.id, tenant_counts))
        for c in calls:
            started = _as_utc(c.started_at) or now
            # Call retention anonymization (stricter, includes transcript wipe)
            if started <= call_cutoff:
                # Count if not already anonymized
                already_anon = c.caller_name == "REDACTED" and c.transcript_json == "[]"
                if not already_anon:
                    total_calls_anonymized += 1
                    tenant_counts["anonymized"] += 1
                    # also counts as transcript purged if had transcript
                    if c.transcript_json and c.transcript_json != "[]":
                        total_transcripts_purged += 1
                        tenant_counts["transcripts"] += 1
                else:
                    # already purged, don't double count
                    pass
                if not dry_run and not already_anon:
                    c.caller_name = "REDACTED"
                    # keep phone but mask? spec says archive/anonymize session records
                    # Anonymize phone to REDACTED for call retention expiry
                    c.caller_phone = "REDACTED"
                    c.transcript_json = "[]"
                    c.reason = ""
                    c.solution = ""
                    c.staff_resolution = ""
                    # Nulling the URL only orphans the audio — the bytes must go.
                    # The deleter never raises; a failed delete is logged inside
                    # it and the row is still anonymized so PII never lingers
                    # in the database waiting on a storage retry.
                    if c.recording_url and deleter(c.recording_url):
                        total_recordings_deleted += 1
                        tenant_counts["recordings"] += 1
                    c.recording_url = None
                continue
            # Transcript-only retention
            if started <= transcript_cutoff:
                has_transcript = bool(c.transcript_json and c.transcript_json != "[]")
                if has_transcript:
                    total_transcripts_purged += 1
                    tenant_counts["transcripts"] += 1
                    if not dry_run:
                        c.transcript_json = "[]"
                        c.reason = ""
                        c.solution = ""

    if not dry_run:
        db.flush()

    # Record audit receipt — one per tenant or one global
    logs = []
    if not dry_run:
        if tenant_id:
            log = RetentionPurgeLog(
                tenant_id=tenant_id,
                purged_by_user_id=triggered_by_user_id,
                execution_type=exec_type,
                records_scanned=total_scanned,
                calls_anonymized=total_calls_anonymized,
                transcripts_purged=total_transcripts_purged,
                recordings_deleted=total_recordings_deleted,
                dry_run=0,
            )
            db.add(log)
            db.flush()
            logs.append(log)
        else:
            for tenant_id_each, counts in per_tenant:
                log = RetentionPurgeLog(
                    tenant_id=tenant_id_each,
                    purged_by_user_id=triggered_by_user_id,
                    execution_type=exec_type,
                    records_scanned=counts["scanned"],
                    calls_anonymized=counts["anonymized"],
                    transcripts_purged=counts["transcripts"],
                    recordings_deleted=counts["recordings"],
                    dry_run=0,
                )
                db.add(log)
                db.flush()
                logs.append(log)

    return {
        "tenant_id": tenant_id,
        "dry_run": dry_run,
        "execution_type": exec_type,
        "records_scanned": total_scanned,
        "calls_anonymized": total_calls_anonymized,
        "transcripts_purged": total_transcripts_purged,
        "recordings_deleted": total_recordings_deleted,
        "logs_created": len(logs),
    }
