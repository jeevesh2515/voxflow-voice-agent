"""VoxFlow - DLQ redrive processor for Connect recordings.

Triggered by the ``voxflow-recordings-dlq`` SQS queue (the on-failure /
permanent-error destination for the S3 recording handler). Re-runs the EXACT
same ``process_record`` path as the S3 handler:

- transient failures raise -> the SQS event-source mapping retries the batch
  (with bisection) up to the queue's maxReceiveCount, then messages move to
  the poison queue via the redrive policy;
- permanent failures are sent on to the poison queue
  (``VOXFLOW_RECORDING_POISON_QUEUE_URL``) so they are quarantined for manual
  inspection, never re-processed indefinitely.

Deploy BOTH files in the same Lambda package (zip containing
s3_recordings_handler.py + dlq_redrive_handler.py) so the import resolves.

Environment variables: same as s3_recordings_handler, plus:
    VOXFLOW_RECORDING_POISON_QUEUE_URL   final quarantine queue (required)
"""

from __future__ import annotations

import json
import os
from typing import Any

from s3_recordings_handler import _log, build_clients, process_record


def lambda_handler(event: dict, context) -> dict:
    api_url = os.environ.get("VOXFLOW_API_URL", "").rstrip("/")
    secret = os.environ.get("VOXFLOW_SECRET", "")
    instance_id = os.environ.get("CONNECT_INSTANCE_ID", "")
    region = os.environ.get("CONNECT_REGION", "eu-west-2")
    poison_url = os.environ.get("VOXFLOW_RECORDING_POISON_QUEUE_URL", "").strip()
    retention_days = int(os.environ.get("VOXFLOW_RECORDING_RETENTION_DAYS", "30"))
    if not poison_url:
        _log("ERROR", "poison_queue_unconfigured")
        raise RuntimeError("VOXFLOW_RECORDING_POISON_QUEUE_URL is required")

    clients = build_clients(region)
    # Permanent failures from the redrive path go to the POISON queue, not back
    # into this queue (avoids an infinite redrive loop).
    ctx = {
        "api_url": api_url,
        "secret": secret,
        "instance_id": instance_id,
        "region": region,
        "retention_days": retention_days,
        **clients,
        "dlq_url": poison_url,
    }

    counts = {"handled": 0, "skipped": 0, "dlqed": 0}
    for msg in event.get("Records", []):
        try:
            body = json.loads(msg.get("body", "{}"))
        except Exception:  # noqa: BLE001
            _log("ERROR", "dlq_invalid_body", msg_id=msg.get("messageId", ""))
            counts["skipped"] += 1
            continue

        records: list[dict[str, Any]] = []
        if isinstance(body, dict) and isinstance(body.get("record"), dict):
            records = [body["record"]]
        elif isinstance(body, dict) and isinstance(body.get("Records"), list):
            records = [r for r in body["Records"] if r.get("eventSource") == "aws:s3"]

        for rec in records:
            res = process_record(rec, ctx)
            status = res.get("status", "skipped")
            counts[status if status in counts else "skipped"] += 1
            if status == "dlqed":
                _log("WARN", "redrive_dlqed", reason=res.get("reason", ""),
                     msg_id=msg.get("messageId", ""))

    _log("INFO", "dlq_batch_done", **counts)
    return counts
