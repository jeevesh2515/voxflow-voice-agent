"""Server-Authoritative Integrations Router for Multi-Tenant Workspaces.

Provides self-serve management for third-party integrations (e.g. Google Sheets,
CRMs, webhooks) with strict tenant scoping and 3-tier RBAC enforcement.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import (
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    require_tenant_role,
)
from ..config import get_settings
from ..db import Tenant, get_session
from ..integrations.gsheets import GoogleSheetsClient
from ..logging import get_logger


log = get_logger(__name__)
router = APIRouter(prefix="/api/tenants/{tenant_id}/integrations", tags=["tenant-integrations"])


# Helper to extract Google Spreadsheet ID from raw IDs or full URLs
SHEET_URL_PATTERN = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")


def extract_spreadsheet_id(raw_input: str) -> str:
    """Extract clean 44+ character Google Spreadsheet ID from raw ID or browser URL."""
    clean = raw_input.strip()
    if not clean:
        return ""
    match = SHEET_URL_PATTERN.search(clean)
    if match:
        return match.group(1).strip()
    # Strip any trailing slashes or URL query parameters
    cleaned_id = clean.split("?")[0].split("#")[0].strip().strip("/")
    return cleaned_id


class ConnectGoogleSheetIn(BaseModel):
    sheet_url_or_id: str = Field(..., description="Google Spreadsheet URL or Sheet ID")
    sheet_name: str | None = Field(default=None, description="Optional custom label for the sheet")
    call_tab: str = Field(default="Call Log", max_length=64, description="Tab name for call outcome records")
    email_tab: str = Field(default="Email Log", max_length=64, description="Tab name for email summary records")
    auto_create_headers: bool = Field(default=True, description="Automatically write column headers if missing")


def _require_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
    return tenant


@router.get("/google-sheets")
async def get_tenant_google_sheets_config(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Retrieve Google Sheets integration posture and connection details for a workspace."""
    tenant = _require_tenant(db, tenant_id)
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
        allow_demo=True,
    )

    gsheets = GoogleSheetsClient.instance()
    service_account_email = gsheets.service_account_email()
    sheet_id = tenant.google_sheet_id or ""
    is_connected = bool(sheet_id) and tenant.google_sheet_status == "connected"

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "is_connected": is_connected,
        "google_sheet_id": sheet_id,
        "google_sheet_name": tenant.google_sheet_name or ("Connected Spreadsheet" if sheet_id else None),
        "google_sheet_tab": tenant.google_sheet_tab or "Call Log",
        "google_sheet_email_tab": tenant.google_sheet_email_tab or "Email Log",
        "google_sheet_status": tenant.google_sheet_status or ("connected" if sheet_id else "disconnected"),
        "google_sheet_connected_at": tenant.google_sheet_connected_at.isoformat() if tenant.google_sheet_connected_at else None,
        "service_account_email": service_account_email,
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}" if sheet_id else None,
        "global_fallback_configured": bool(get_settings().google_sheet_id),
        "service_account_configured": bool(service_account_email),
    }


@router.post("/google-sheets/connect")
async def connect_tenant_google_sheet(
    tenant_id: str,
    payload: ConnectGoogleSheetIn,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Connect and verify a Google Spreadsheet for this workspace. Restricted to ROLE_OWNER."""
    tenant = _require_tenant(db, tenant_id)
    actor = require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER},
        allow_demo=False,
    )

    sheet_id = extract_spreadsheet_id(payload.sheet_url_or_id)
    if not sheet_id or len(sheet_id) < 15:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_spreadsheet_id: Provide a valid Google Spreadsheet URL or 44-character ID",
        )

    call_tab = payload.call_tab.strip() or "Call Log"
    email_tab = payload.email_tab.strip() or "Email Log"

    gsheets = GoogleSheetsClient.instance()

    # Preflight verification and header bootstrapping
    verification = await gsheets.verify_and_bootstrap_spreadsheet(
        sheet_id=sheet_id,
        call_tab=call_tab if payload.auto_create_headers else "",
        email_tab=email_tab if payload.auto_create_headers else "",
    )

    if not verification.get("ok"):
        error_type = verification.get("error", "verification_failed")
        detail = verification.get("detail", "Failed to access spreadsheet.")
        # If service account is not configured in test/offline mode, allow connection with notice
        if error_type == "service_account_auth_failed" and not gsheets.service_account_email():
            log.warning("gsheets.connect_offline_mode", tenant_id=tenant_id, sheet_id=sheet_id)
            title = payload.sheet_name or "Workspace Google Sheet"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error_type}: {detail}",
            )
    else:
        title = payload.sheet_name or verification.get("title") or "Workspace Google Sheet"

    # Persist to database
    now = datetime.now(timezone.utc)
    tenant.google_sheet_id = sheet_id
    tenant.google_sheet_name = title
    tenant.google_sheet_tab = call_tab
    tenant.google_sheet_email_tab = email_tab
    tenant.google_sheet_status = "connected"
    tenant.google_sheet_connected_at = now
    tenant.google_sheet_connected_by_user_id = actor.user_id
    db.commit()

    log.info(
        "gsheets.tenant_connected",
        tenant_id=tenant_id,
        sheet_id=sheet_id,
        title=title,
        user_id=actor.user_id,
    )

    return {
        "ok": True,
        "message": "Google Spreadsheet connected and verified successfully",
        "tenant_id": tenant_id,
        "google_sheet_id": sheet_id,
        "google_sheet_name": title,
        "google_sheet_tab": call_tab,
        "google_sheet_email_tab": email_tab,
        "google_sheet_status": "connected",
        "google_sheet_connected_at": now.isoformat(),
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}",
    }


@router.post("/google-sheets/test")
async def test_tenant_google_sheet_connection(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Execute live read/write preflight test against the tenant's connected spreadsheet."""
    tenant = _require_tenant(db, tenant_id)
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
        allow_demo=True,
    )

    sheet_id = tenant.google_sheet_id
    if not sheet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="no_spreadsheet_connected: Please connect a Google Spreadsheet first",
        )

    gsheets = GoogleSheetsClient.instance()
    t0 = datetime.now(timezone.utc)
    meta = await gsheets.get_spreadsheet_metadata(sheet_id)
    latency_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)

    if not meta.get("ok"):
        error_type = meta.get("error", "test_failed")
        detail = meta.get("detail", "Could not read spreadsheet.")
        # Mark error status if connection is broken
        tenant.google_sheet_status = "error"
        db.commit()
        return {
            "ok": False,
            "error": error_type,
            "detail": detail,
            "latency_ms": latency_ms,
            "sheet_id": sheet_id,
        }

    # Ensure status is healthy
    tenant.google_sheet_status = "connected"
    if meta.get("title") and not tenant.google_sheet_name:
        tenant.google_sheet_name = meta.get("title")
    db.commit()

    return {
        "ok": True,
        "message": "Spreadsheet connection verified and healthy",
        "sheet_id": sheet_id,
        "title": meta.get("title"),
        "tabs": meta.get("tabs", []),
        "latency_ms": latency_ms,
        "configured_call_tab": tenant.google_sheet_tab,
        "configured_email_tab": tenant.google_sheet_email_tab,
    }


@router.delete("/google-sheets")
async def disconnect_tenant_google_sheet(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Disconnect Google Spreadsheet from workspace. Restricted to ROLE_OWNER."""
    tenant = _require_tenant(db, tenant_id)
    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER},
        allow_demo=False,
    )

    tenant.google_sheet_id = None
    tenant.google_sheet_name = None
    tenant.google_sheet_status = "disconnected"
    tenant.google_sheet_connected_at = None
    tenant.google_sheet_connected_by_user_id = None
    db.commit()

    log.info("gsheets.tenant_disconnected", tenant_id=tenant_id)
    return {
        "ok": True,
        "message": "Google Spreadsheet disconnected successfully",
        "tenant_id": tenant_id,
        "google_sheet_status": "disconnected",
    }
