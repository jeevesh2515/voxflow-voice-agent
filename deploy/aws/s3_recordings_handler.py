"""VoxFlow - Amazon Connect call-recording S3 event handler.

Amazon Connect delivers call recordings into the instance's S3 bucket
AFTER the call ends (post-call delivery), SSE-KMS encrypted, with a
key layout of date plus contact-id:
    connect/<instance>/<yyyy>/<mm>/<dd>/<contact-id>/<recording-file>

This handler reacts to the S3 ``s3:ObjectCreated:*`` event on that bucket:
1. extracts the contact ID from the object key;
2. reads the IVR consent attributes written by the contact flow
   (``consent_granted`` / ``consent_recorded``) via
   ``connect:GetContactAttributes`` (contact attributes persist ~24 months);
3. tags the object with consent + retention evidence (drives S3 lifecycle);
4. HMAC-POSTs the evidence to VoxFlow's ``/api/connect/recording`` so the
   server persists ``recording_url`` + ``consent_evidence_ref`` and updates
   the recipient consent ledger.

Environment variables:
    VOXFLOW_API_URL                  base URL of the always-on VoxFlow API
    VOXFLOW_SECRET                   shared HMAC secret (== CONNECT_LAMBDA_SECRET)
    CONNECT_INSTANCE_ID              Amazon Connect instance id
    CONNECT_REGION                   e.g. eu-west-2
    VOXFLOW_RECORDING_RETENTION_DAYS default 30
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

_CONTACT_ID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_RETENTION_DAYS = int(os.environ.get("VOXFLOW_RECORDING_RETENTION_DAYS", "30"))
_RECORDING_EXTS = (".wav", ".mp3", ".flac", ".ogg")


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
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < tries:
                time.sleep(2**attempt)

    if last_err is not None:
        raise last_err
    raise RuntimeError("recording ingest failed")


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


def lambda_handler(event: dict, context) -> dict:
    api_url = os.environ.get("VOXFLOW_API_URL", "").rstrip("/")
    secret = os.environ.get("VOXFLOW_SECRET", "")
    instance_id = os.environ.get("CONNECT_INSTANCE_ID", "")
    region = os.environ.get("CONNECT_REGION", "eu-west-2")

    import boto3  # deferred so imports stay cheap when unused

    connect_client = boto3.client("connect", region_name=region)
    s3_client = boto3.client("s3", region_name=region)

    handled = 0
    for record in event.get("Records", []):
        if record.get("eventSource") != "aws:s3":
            continue
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        if not _is_recording_key(key) or not instance_id:
            continue

        contact_id = _extract_contact_id(key)
        if not contact_id:
            print(f"WARN no_contact_id_in_key bucket={bucket} key={key}")  # noqa: T201
            continue

        consent_granted = "false"
        consent_recorded = "false"
        try:
            resp = connect_client.get_contact_attributes(
                InstanceId=instance_id, InitialContactId=contact_id
            )
            attrs = resp.get("Attributes", {}) or {}
            consent_granted = str(attrs.get("consent_granted", "false")).lower()
            consent_recorded = str(attrs.get("consent_recorded", "false")).lower()
        except Exception as exc:  # noqa: BLE001
            print(f"WARN get_contact_attributes_failed contact={contact_id} err={exc}")  # noqa: T201
            continue

        expiry = (datetime.now(timezone.utc) + timedelta(days=_RETENTION_DAYS)).date().isoformat()
        try:
            s3_client.put_object_tagging(
                Bucket=bucket,
                Key=key,
                Tagging={
                    "TagSet": [
                        {"Key": "voxflow:consent", "Value": consent_granted},
                        {"Key": "voxflow:recorded", "Value": consent_recorded},
                        {"Key": "voxflow:retention-until", "Value": expiry},
                        {"Key": "voxflow:contact-id", "Value": contact_id},
                    ]
                },
            )
        except Exception as exc:  # noqa: BLE001
            print(f"WARN tag_recording_failed bucket={bucket} key={key} err={exc}")  # noqa: T201

        payload = {
            "contact_id": contact_id,
            "bucket": bucket,
            "s3_key": key,
            "recording_url": f"s3://{bucket}/{key}",
            "instance_id": instance_id,
            "region": region,
            "consent_granted": consent_granted == "true",
            "consent_recorded": consent_recorded == "true",
        }

        try:
            _post_json(f"{api_url}/api/connect/recording", payload, secret, "/api/connect/recording")
            handled += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR persist_recording_failed contact={contact_id} err={exc}")  # noqa: T201
            raise  # let S3 redeliver the event

    return {"statusCode": 200, "handled": handled}
