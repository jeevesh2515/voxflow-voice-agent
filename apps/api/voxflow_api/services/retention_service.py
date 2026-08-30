"""Retention purge — scrub expired transcripts/calls, idempotent, dry-run safe."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..db import Call, RetentionPurgeLog, Tenant


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

    exec_type = execution_type or ("manual_trigger" if triggered_by_user_id else "automated_cron")

    for tenant in tenants:
        transcript_days = getattr(tenant, "transcript_retention_days", 30) or 30
        call_days = getattr(tenant, "call_retention_days", 90) or 90
        transcript_cutoff = now - timedelta(days=transcript_days)
        call_cutoff = now - timedelta(days=call_days)

        calls = db.query(Call).filter(Call.tenant_id == tenant.id).all()
        total_scanned += len(calls)
        for c in calls:
            started = _as_utc(c.started_at) or now
            # Call retention anonymization (stricter, includes transcript wipe)
            if started <= call_cutoff:
                # Count if not already anonymized
                already_anon = c.caller_name == "REDACTED" and c.transcript_json == "[]"
                if not already_anon:
                    total_calls_anonymized += 1
                    # also counts as transcript purged if had transcript
                    if c.transcript_json and c.transcript_json != "[]":
                        total_transcripts_purged += 1
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
                    c.recording_url = None
                continue
            # Transcript-only retention
            if started <= transcript_cutoff:
                has_transcript = bool(c.transcript_json and c.transcript_json != "[]")
                if has_transcript:
                    total_transcripts_purged += 1
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
                dry_run=0,
            )
            db.add(log)
            db.flush()
            logs.append(log)
        else:
            for tenant in tenants:
                log = RetentionPurgeLog(
                    tenant_id=tenant.id,
                    purged_by_user_id=triggered_by_user_id,
                    execution_type=exec_type,
                    records_scanned=total_scanned,
                    calls_anonymized=total_calls_anonymized,
                    transcripts_purged=total_transcripts_purged,
                    dry_run=0,
                )
                db.add(log)
                db.flush()
                logs.append(log)
                break

    return {
        "tenant_id": tenant_id,
        "dry_run": dry_run,
        "execution_type": exec_type,
        "records_scanned": total_scanned,
        "calls_anonymized": total_calls_anonymized,
        "transcripts_purged": total_transcripts_purged,
        "logs_created": len(logs),
    }
