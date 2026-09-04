"""VoxFlow - Amazon Connect call-recording S3 event handler (retry + DLQ).

Amazon Connect delivers call recordings into the instance's S3 bucket AFTER
the call ends (post-call delivery), SSE-KMS encrypted, key layout:

    connect/<instance>/<yyyy>/<mm>/<dd>/<contact-id>/<recording-file>

Reacts to S3 ``s3:ObjectCreated:*`` events:
1. extracts the contact ID from the object key;
2. reads the IVR consent attributes written by the contact flow
   (``consent_granted`` / ``consent_recorded``) via ``connect:GetContactAttributes``;
3. tags the object with consent + retention evidence (drives S3 lifecycle);
4. HMAC-POSTs the evidence to VoxFlow's ``/api/connect/recording``.

Failure handling (this file):
- TRANSIENT errors (S3/Connect throttling, KMS/SlowDown, network timeouts,
  5xx) are retried in-process with exponential backoff + jitter; if still
  failing the handler raises so Lambda's asynchronous invocation retries
  (max 2 retries, events retained up to 6h), and finally the on-failure
  destination delivers the event to the DLQ.
- PERMANENT errors (NoSuchKey, AccessDenied, ResourceNotFound, malformed
  attributes, API 4xx) are sent straight to the SQS DLQ (best-effort) so
  they never burn retry budget.

Environment variables:
    VOXFLOW_API_URL                   base URL of the always-on VoxFlow API
    VOXFLOW_SECRET                    shared HMAC secret (== CONNECT_LAMBDA_SECRET)
    CONNECT_INSTANCE_ID               Amazon Connect instance id
    CONNECT_REGION                    e.g. eu-west-2
    VOXFLOW_RECORDING_RETENTION_DAYS  default 30
    VOXFLOW_RECORDING_DLQ_URL         SQS DLQ URL (recommended). Optional;
                                      if unset, permanent failures are logged.
    VOXFLOW_RETRY_ATTEMPTS            in-process transient retries (default 3)
"""

from __future__ import annotations

import functools
import hashlib
import hmac
import json
import os
import random
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

_CONTACT_ID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_RETENTION_DAYS = int(os.environ.get("VOXFLOW_RECORDING_RETENTION_DAYS", "30"))
_RETRY_ATTEMPTS = int(os.environ.get("VOXFLOW_RETRY_ATTEMPTS", "3"))
_RECORDING_EXTS = (".wav", ".mp3", ".flac", ".ogg")
_TRANSIENT_CODES = frozenset({"429", "500", "502", "503", "504"})
_TRANSIENT_CODE_HINTS = ("Throttl", "SlowDown", "Time", "Limit", "Unavailable", "Internal", "Service")


def _log(level: str, event: str, **kv: Any) -> None:
    parts = " ".join(f"{k}={v}" for k, v in kv.items())
    print(f"{level} {event} {parts}")  # noqa: T201


# ---------------------------------------------------------------- classification
def _classify_error(exc: Exception) -> str:
    """Return 'transient' (retryable) or 'permanent' (send straight to DLQ)."""
    if isinstance(exc, (_ApiError,)):
        if exc.status and exc.status == 429:
            return "transient"
        if exc.status and exc.status >= 500:
            return "transient"
        return "permanent"
    if isinstance(exc, (ConnectionError, TimeoutError, socket.timeout, urllib.error.URLError)):
        return "transient"
    resp = getattr(exc, "response", None)
    if isinstance(resp, dict):
        err = resp.get("Error") or {}
        code = str(err.get("Code", ""))
        status = int((resp.get("ResponseMetadata") or {}).get("HTTPStatusCode", 0) or 0)
        if status in _TRANSIENT_CODES:
            return "transient"
        if code and any(hint in code for hint in _TRANSIENT_CODE_HINTS):
            return "transient"
        return "permanent"
    # Unknown exception type: retry it (safe default; DLQ still catches repeats).
    return "transient"


class _ApiError(Exception):
    """Raised by _post_json so the caller can classify HTTP status."""

    def __init__(self, status: int, body: str = "") -> None:
        super().__init__(f"api_status={status} body={body[:200]}")
        self.status = status


# ---------------------------------------------------------------- retry wrapper
def retry_transient(tries: int = _RETRY_ATTEMPTS, base_delay: float = 0.5,
                    max_delay: float = 8.0, jitter: float = 0.3) -> Callable:
    """Retry a function only on transient errors, with exp. backoff + jitter."""

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last: Exception | None = None
            for attempt in range(1, tries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last = exc
                    if _classify_error(exc) != "transient":
                        raise
                    if attempt == tries:
                        break
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    delay *= 1.0 + random.uniform(0, jitter)
                    _log("WARN", "retry_transient", fn=fn.__name__, attempt=attempt,
                         delay_ms=int(delay * 1000), err=str(exc).splitlines()[0][:160])
                    time.sleep(delay)
            assert last is not None
            raise last
        return wrapper

    return deco


# ---------------------------------------------------------------- signing / POST
def _sign_request(secret: str, timestamp: str, path: str, body: bytes) -> str:
    message = timestamp.encode("utf-8") + b":" + path.encode("utf-8") + b":" + body
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _post_json(url: str, payload: dict, secret: str, path: str, *, tries: int = 3) -> dict:
    if not secret:
        raise RuntimeError("VOXFLOW_SECRET is required")
    data = json.dumps(payload).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(1, tries + 1):
        timestamp = str(time.time())
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "VoxFlow-AWS-Recordings-Handler/1.0",
            "x-voxflow-signature": _sign_request(secret, timestamp, path, data),
            "x-voxflow-timestamp": timestamp,
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_err = _ApiError(exc.code, exc.read()[:200].decode("utf-8", "replace"))
            if _classify_error(last_err) == "transient" and attempt < tries:
                time.sleep(2 ** attempt)
                continue
            break
        except Exception as exc:  # noqa: BLE001 (network/timeout/URLError)
            last_err = exc
            if attempt < tries:
                time.sleep(2 ** attempt)
                continue
            break
    if last_err is not None:
        raise last_err
    raise RuntimeError("recording ingest failed")


# ---------------------------------------------------------------- key parsing
def _extract_contact_id(key: str) -> str | None:
    match = _CONTACT_ID_RE.search(key)
    if match:
        return match.group(0)
    parts = [p for p in key.split("/") if p]
    for idx, part in enumerate(parts):
        if re.fullmatch(r"\d{4}", part) and idx + 3 < len(parts):
            candidate = parts[idx + 3]
            if candidate and "." not in candidate:
                return candidate
    return None


def _is_recording_key(key: str) -> bool:
    lowered = key.lower()
    return lowered.startswith("connect/") and lowered.endswith(_RECORDING_EXTS)


# ---------------------------------------------------------------- AWS helpers
@retry_transient()
def _read_tags(s3: Any, bucket: str, key: str) -> dict[str, str]:
    resp = s3.get_object_tagging(Bucket=bucket, Key=key)
    return {t["Key"]: t["Value"] for t in resp.get("TagSet", [])}


@retry_transient()
def _write_tags(s3: Any, bucket: str, key: str, tagset: dict[str, str]) -> None:
    s3.put_object_tagging(
        Bucket=bucket, Key=key,
        Tagging={"TagSet": [{"Key": k, "Value": v} for k, v in tagset.items()]},
    )


def _set_tags(s3: Any, bucket: str, key: str, extra: dict[str, str]) -> None:
    tags = _read_tags(s3, bucket, key)
    tags.update(extra)
    _write_tags(s3, bucket, key, tags)


def _already_posted(s3: Any, bucket: str, key: str) -> bool:
    """Idempotency guard keyed on contact_id (object key): never double-POST."""
    return _read_tags(s3, bucket, key).get("voxflow:post-status") == "ok"


def _mark_posted(s3: Any, bucket: str, key: str) -> None:
    _set_tags(s3, bucket, key, {"voxflow:post-status": "ok"})


@retry_transient()
def _fetch_consent(connect: Any, instance_id: str, contact_id: str) -> tuple[bool, bool]:
    resp = connect.get_contact_attributes(InstanceId=instance_id, InitialContactId=contact_id)
    attrs = resp.get("Attributes", {}) or {}
    granted = str(attrs.get("consent_granted", "false")).lower() == "true"
    recorded = str(attrs.get("consent_recorded", "false")).lower() == "true"
    return granted, recorded


def _send_to_dlq(sqs: Any, queue_url: str, record: dict, reason: str,
                 extra: dict | None = None) -> None:
    """Best-effort send to the SQS DLQ; never raises into the retry path."""
    if not queue_url or sqs is None:
        _log("ERROR", "dlq_unconfigured", reason=reason)
        return
    body: dict[str, Any] = {
        "type": "connect-recording-s3",
        "reason": reason,
        "permanent": True,
        "ts": datetime.now(timezone.utc).isoformat(),
        "record": record,
    }
    if extra:
        body["payload"] = extra
    try:
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(body))
        _log("INFO", "dlq_sent", reason=reason)
    except Exception as exc:  # noqa: BLE001
        _log("ERROR", "dlq_send_failed", reason=reason, err=str(exc)[:160])


def build_clients(region: str) -> dict[str, Any]:
    import boto3  # deferred so module import stays cheap outside Lambda
    clients: dict[str, Any] = {
        "connect": boto3.client("connect", region_name=region),
        "s3": boto3.client("s3", region_name=region),
    }
    dlq_url = os.environ.get("VOXFLOW_RECORDING_DLQ_URL", "")
    clients["sqs"] = boto3.client("sqs", region_name=region) if dlq_url else None
    clients["dlq_url"] = dlq_url
    return clients


# ---------------------------------------------------------------- core
def process_record(record: dict, ctx: dict[str, Any]) -> dict[str, Any]:
    """Process one S3 event record. Raises on transient error (async retry /
    DLQ destination); sends permanent errors to the DLQ and continues."""
    if record.get("eventSource") != "aws:s3":
        return {"status": "skipped", "reason": "not_s3_event"}
    bucket = record["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
    if not _is_recording_key(key) or not ctx.get("instance_id"):
        return {"status": "skipped", "reason": "not_recording_key"}
    contact_id = _extract_contact_id(key)
    if not contact_id:
        return {"status": "skipped", "reason": "no_contact_id"}
    try:
        if _already_posted(ctx["s3"], bucket, key):
            return {"status": "skipped", "reason": "already_posted"}
    except Exception as exc:  # noqa: BLE001
        _log("WARN", "idempotency_check_failed", key=key, err=str(exc)[:160])

    try:
        consent_granted, consent_recorded = _fetch_consent(
            ctx["connect"], ctx["instance_id"], contact_id
        )
    except Exception as exc:  # noqa: BLE001
        kind = _classify_error(exc)
        _log("WARN", "consent_fetch_failed", contact_id=contact_id, kind=kind, err=str(exc)[:160])
        if kind == "transient":
            raise
        _send_to_dlq(ctx.get("sqs"), ctx.get("dlq_url"), record,
                     reason=f"permanent_consent_fetch:{type(exc).__name__}")
        return {"status": "dlqed", "reason": "permanent_consent_fetch"}

    expiry = (datetime.now(timezone.utc) + timedelta(days=ctx["retention_days"])).date().isoformat()
    try:
        _set_tags(ctx["s3"], bucket, key, {
            "voxflow:consent": "true" if consent_granted else "false",
            "voxflow:recorded": "true" if consent_recorded else "false",
            "voxflow:retention-until": expiry,
            "voxflow:contact-id": contact_id,
        })
    except Exception as exc:  # noqa: BLE001
        kind = _classify_error(exc)
        _log("WARN", "tag_failed", key=key, kind=kind, err=str(exc)[:160])
        if kind == "transient":
            raise
        _send_to_dlq(ctx.get("sqs"), ctx.get("dlq_url"), record,
                     reason=f"permanent_tag:{type(exc).__name__}")
        return {"status": "dlqed", "reason": "permanent_tag"}

    payload = {
        "contact_id": contact_id,
        "bucket": bucket,
        "s3_key": key,
        "recording_url": f"s3://{bucket}/{key}",
        "instance_id": ctx["instance_id"],
        "region": ctx["region"],
        "consent_granted": consent_granted,
        "consent_recorded": consent_recorded,
    }
    try:
        _post_json(f"{ctx['api_url']}/api/connect/recording", payload,
                   ctx["secret"] or "", "/api/connect/recording")
    except _ApiError as exc:
        _log("ERROR", "persist_api_failed", contact_id=contact_id,
             status=exc.status, err=str(exc)[:160])
        if exc.status and exc.status != 429 and 400 <= exc.status < 500:
            _send_to_dlq(ctx.get("sqs"), ctx.get("dlq_url"), record,
                         reason=f"permanent_api:{exc.status}", extra=payload)
            return {"status": "dlqed", "reason": f"permanent_api:{exc.status}"}
        raise
    except Exception as exc:  # noqa: BLE001 (network / timeout -> transient)
        _log("ERROR", "persist_network_failed", contact_id=contact_id, err=str(exc)[:160])
        raise

    try:
        _mark_posted(ctx["s3"], bucket, key)
    except Exception as exc:  # noqa: BLE001
        _log("WARN", "mark_posted_failed", key=key, err=str(exc)[:160])

    _log("INFO", "recording_handled", contact_id=contact_id)
    return {"status": "handled", "contact_id": contact_id}


def lambda_handler(event: dict, context) -> dict:
    api_url = os.environ.get("VOXFLOW_API_URL", "").rstrip("/")
    secret = os.environ.get("VOXFLOW_SECRET", "")
    instance_id = os.environ.get("CONNECT_INSTANCE_ID", "")
    region = os.environ.get("CONNECT_REGION", "eu-west-2")
    clients = build_clients(region)
    ctx = {
        "api_url": api_url, "secret": secret, "instance_id": instance_id,
        "region": region, "retention_days": _RETENTION_DAYS, **clients,
    }
    counts = {"handled": 0, "skipped": 0, "dlqed": 0}
    for record in event.get("Records", []):
        res = process_record(record, ctx)
        status = res.get("status", "skipped")
        counts[status if status in counts else "skipped"] += 1
        if status == "dlqed":
            _log("WARN", "record_dlqed", reason=res.get("reason", ""))
    _log("INFO", "s3_batch_done", **counts)
    return {"statusCode": 200, **counts}
