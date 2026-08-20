"""Outbound Webhook Integration Engine for Client ERPs & CRMs.

Dispatches signed HTTP POST events asynchronously when key call actions occur:
  - order_created / po_signed
  - appointment_booked
  - call_escalated
  - call_outcome_logged
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx

from ..db import Tenant, async_session_scope
from ..logging import get_logger


log = get_logger(__name__)


async def _get_tenant_webhook_config(tenant_id: str) -> tuple[str | None, str | None]:
    """Retrieve webhook_url and webhook_secret for the active tenant."""
    try:
        async with async_session_scope() as db:
            tenant = await db.get(Tenant, tenant_id)
            if tenant and tenant.webhook_url:
                return tenant.webhook_url, tenant.webhook_secret
    except Exception as e:
        log.warning("webhook.fetch_config_failed", tenant_id=tenant_id, error=str(e))
    return None, None


def _compute_signature(secret: str, payload_bytes: bytes) -> str:
    """Generate HMAC-SHA256 signature for payload verification."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


async def dispatch_webhook(tenant_id: str, event_type: str, payload: dict[str, Any]) -> bool:
    """Asynchronously dispatch an event to the client's configured webhook URL.

    Never blocks the caller event loop or raises exceptions.
    """
    url, secret = await _get_tenant_webhook_config(tenant_id)
    if not url:
        return False

    body = {
        "event": event_type,
        "tenant_id": tenant_id,
        "timestamp": int(time.time()),
        "data": payload,
    }
    raw_body = json.dumps(body, default=str).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "VoxFlow-Webhook/1.0",
    }
    if secret:
        signature = _compute_signature(secret, raw_body)
        headers["X-VoxFlow-Signature"] = signature

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(url, content=raw_body, headers=headers)
            log.info(
                "webhook.dispatched",
                tenant_id=tenant_id,
                event=event_type,
                status=resp.status_code,
            )
            return 200 <= resp.status_code < 300
    except Exception as e:
        log.warning(
            "webhook.dispatch_failed",
            tenant_id=tenant_id,
            event=event_type,
            error=str(e),
        )
        return False


def dispatch_webhook_background(tenant_id: str, event_type: str, payload: dict[str, Any]) -> None:
    """Deprecated Day 34 safety shim; it never performs a fire-and-forget POST.

    New callers must persist a trusted aggregate and enqueue `crm.webhook.sync`
    through the side-effect ledger. The no-op avoids reintroducing direct
    external HTTP ownership while legacy extensions are migrated.
    """

    del payload
    log.warning(
        "webhook.direct_dispatch_disabled",
        tenant_id=tenant_id,
        event=event_type,
        required_job_type="crm.webhook.sync",
    )
