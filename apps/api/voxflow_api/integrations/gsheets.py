"""Google Sheets writer for the call-outcome log with persistent retry queue.

Design notes
------------
* **Non-blocking.** The service-account token refresh is synchronous (it's
  `google-auth`), so it runs in a worker thread. The actual Sheets API calls
  go out over `httpx.AsyncClient`. Nothing here blocks the event loop, which
  matters because this runs while a human is on the phone.

* **Never fatal.** Every public method returns a result dict and swallows its
  own exceptions. A Google outage, a revoked key, or a deleted spreadsheet
  must degrade to "the row didn't reach Sheets" — never "the call dropped".
  Postgres remains the source of truth; Sheets is the human-facing mirror.

* **Persistent Retry Queue.** Failed writes are persisted to `{data_dir}/sheets_queue/*.json`.
  A background worker retries them automatically until synced. Zero lost rows.

* **Token reuse.** Tokens are cached until 60s before expiry, so a busy call
  centre isn't re-minting JWTs on every row.
"""

from __future__ import annotations

import asyncio
import glob
import json
import os
import time
import uuid
from typing import Any

import httpx

from ..config import get_settings
from ..logging import get_logger


log = get_logger(__name__)

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Column order for the call-outcome log. Changing this changes the sheet
# layout — if you add a column, add it at the END so existing rows stay aligned.
CALL_LOG_HEADERS = [
    "Timestamp (IST)",
    "Call ID",
    "Caller Phone",
    "Caller Name",
    "Company",
    "Identity Verified",
    "Language",
    "Reason for Call",
    "Solution Given",
    "Resolution Status",
    "Satisfaction",
    "Follow-up Required",
    "Escalated",
    "Duration (sec)",
    "Related Order",
    # Day 42 additions — appended, never reordered.
    "Tenant",
    "Question",
    "Answer",
    "Turn Latency (ms)",
]

EMAIL_LOG_HEADERS = [
    "Timestamp (IST)",
    "Message ID",
    "Sender",
    "Subject",
    "Category",
    "Priority",
    "AI Summary",
    "Action Required",
    "Linked Order/PO",
]


def _queue_dir() -> str:
    s = get_settings()
    d = os.path.join(s.resolved_data_dir, "sheets_queue")
    os.makedirs(d, exist_ok=True)
    return d


class GoogleSheetsClient:
    """Minimal async Sheets v4 client scoped to what VoxFlow needs."""

    _instance: GoogleSheetsClient | None = None

    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._lock = asyncio.Lock()
        self._header_checked: set[str] = set()

    @classmethod
    def instance(cls) -> GoogleSheetsClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ---------- configuration ----------

    @staticmethod
    def _credentials_info() -> dict[str, Any] | None:
        """Load the service-account dict from env JSON or a file path."""
        s = get_settings()
        raw = (s.google_service_account_json or "").strip()
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                log.error("gsheets.bad_service_account_json", error=str(e))
                return None

        path = (s.google_service_account_file or "").strip()
        if path:
            try:
                with open(path, encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception as e:
                log.error("gsheets.service_account_file_unreadable", path=path, error=str(e))
                return None
        return None

    @classmethod
    def service_account_email(cls) -> str:
        """Return the configured service account email for display in the dashboard."""
        info = cls._credentials_info()
        if info and isinstance(info, dict):
            return str(info.get("client_email", "") or "")
        return ""

    @classmethod
    def is_configured(cls) -> bool:
        s = get_settings()
        if not s.sheets_enabled:
            return False
        if not s.google_sheet_id:
            # Service account may still be configured for per-tenant sheets
            return cls._credentials_info() is not None
        return cls._credentials_info() is not None

    # ---------- auth ----------

    def _mint_token_sync(self) -> tuple[str, float] | None:
        """Blocking token mint — always called via asyncio.to_thread."""
        info = self._credentials_info()
        if info is None:
            return None
        try:
            from google.auth.transport.requests import Request  # type: ignore[import-not-found]
            from google.oauth2 import service_account  # type: ignore[import-not-found]
        except ImportError:
            log.error("gsheets.google_auth_missing", hint="pip install google-auth")
            return None

        try:
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            creds.refresh(Request())
            expiry = creds.expiry.timestamp() if creds.expiry else time.time() + 3000
            return str(creds.token), float(expiry)
        except Exception as e:
            log.error("gsheets.token_refresh_failed", error=str(e))
            return None

    async def _get_token(self) -> str | None:
        async with self._lock:
            if self._token and time.time() < self._token_expiry - 60:
                return self._token
            result = await asyncio.to_thread(self._mint_token_sync)
            if result is None:
                return None
            self._token, self._token_expiry = result
            return self._token

    # ---------- sheet operations ----------

    @staticmethod
    def _a1(tab: str, ref: str) -> str:
        """Quote a tab name for A1 notation."""
        if not tab.replace("_", "").isalnum():
            tab = "'" + tab.replace("'", "''") + "'"
        return f"{tab}!{ref}"

    async def get_spreadsheet_metadata(self, sheet_id: str) -> dict[str, Any]:
        """Fetch title and sheet tab names for a spreadsheet."""
        token = await self._get_token()
        if not token:
            return {"ok": False, "error": "service_account_auth_failed", "detail": "Google Service Account credentials not configured on server"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(
                    f"{SHEETS_API}/{sheet_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"fields": "properties.title,sheets.properties.title"},
                )
                if r.status_code == 200:
                    data = r.json()
                    title = data.get("properties", {}).get("title", "Untitled Spreadsheet")
                    tabs = [sh["properties"]["title"] for sh in data.get("sheets", []) if "properties" in sh and "title" in sh["properties"]]
                    return {"ok": True, "title": title, "tabs": tabs}
                if r.status_code == 404:
                    return {"ok": False, "error": "spreadsheet_not_found", "detail": "Spreadsheet ID not found or URL invalid."}
                if r.status_code == 403:
                    email = self.service_account_email()
                    return {
                        "ok": False,
                        "error": "permission_denied",
                        "detail": f"Permission denied. Please open Google Sheets > Share > and add '{email or 'the service account'}' with Editor access.",
                    }
                return {"ok": False, "error": f"http_{r.status_code}", "detail": r.text[:200]}
        except Exception as e:
            return {"ok": False, "error": "network_exception", "detail": str(e)}

    async def verify_and_bootstrap_spreadsheet(
        self,
        sheet_id: str,
        call_tab: str = "Call Log",
        email_tab: str = "Email Log",
    ) -> dict[str, Any]:
        """Verify access to spreadsheet and bootstrap headers if missing."""
        meta = await self.get_spreadsheet_metadata(sheet_id)
        if not meta.get("ok"):
            return meta

        token = await self._get_token()
        if not token:
            return {"ok": False, "error": "auth_failed"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if call_tab:
                    await self._ensure_header(client, token, call_tab, CALL_LOG_HEADERS, target_sheet_id=sheet_id)
                if email_tab:
                    await self._ensure_header(client, token, email_tab, EMAIL_LOG_HEADERS, target_sheet_id=sheet_id)

            return {
                "ok": True,
                "title": meta.get("title"),
                "tabs": meta.get("tabs"),
                "call_tab": call_tab,
                "email_tab": email_tab,
            }
        except Exception as e:
            return {"ok": False, "error": "bootstrap_failed", "detail": str(e)}

    async def _ensure_tab(self, client: httpx.AsyncClient, token: str, tab: str, target_sheet_id: str | None = None) -> bool:
        """Create the tab if the spreadsheet does not have it yet."""
        s = get_settings()
        sid = target_sheet_id or s.google_sheet_id
        if not sid:
            return False
        auth = {"Authorization": f"Bearer {token}"}
        r = await client.get(
            f"{SHEETS_API}/{sid}",
            headers=auth,
            params={"fields": "sheets.properties.title"},
        )
        if r.status_code != 200:
            log.warning("gsheets.metadata_read_failed", status=r.status_code, body=r.text[:200])
            return False
        titles = [sh["properties"]["title"] for sh in r.json().get("sheets", [])]
        if tab in titles:
            return True

        r = await client.post(
            f"{SHEETS_API}/{sid}:batchUpdate",
            headers=auth,
            json={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
        )
        if r.status_code >= 300:
            log.warning("gsheets.tab_create_failed", tab=tab, status=r.status_code, body=r.text[:200])
            return False
        log.info("gsheets.tab_created", tab=tab, existing=titles)
        return True

    async def _ensure_header(
        self,
        client: httpx.AsyncClient,
        token: str,
        tab: str,
        headers: list[str],
        target_sheet_id: str | None = None,
    ) -> None:
        """Create the tab and write the header row, once per process."""
        s = get_settings()
        sid = target_sheet_id or s.google_sheet_id
        if not sid:
            return
        cache_key = f"{sid}:{tab}"
        if cache_key in self._header_checked:
            return
        self._header_checked.add(cache_key)

        await self._ensure_tab(client, token, tab, target_sheet_id=sid)

        rng = self._a1(tab, "A1:Z1")
        try:
            r = await client.get(
                f"{SHEETS_API}/{sid}/values/{rng}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code != 200:
                log.warning("gsheets.header_read_failed", status=r.status_code, body=r.text[:200])
                return
            if r.json().get("values"):
                return  # already has a header

            await client.put(
                f"{SHEETS_API}/{sid}/values/{rng}",
                headers={"Authorization": f"Bearer {token}"},
                params={"valueInputOption": "USER_ENTERED"},
                json={"values": [headers]},
            )
            log.info("gsheets.header_written", tab=tab)
        except Exception as e:
            log.warning("gsheets.header_ensure_failed", error=str(e))

    async def append_row(
        self,
        values: list[Any],
        tab: str | None = None,
        headers: list[str] | None = None,
        target_sheet_id: str | None = None,
    ) -> dict[str, Any]:
        """Append one row to the configured spreadsheet. Never raises."""
        s = get_settings()
        sid = target_sheet_id or s.google_sheet_id
        if not sid:
            return {"ok": False, "reason": "sheets_not_configured"}

        tab = tab or s.google_sheet_tab
        token = await self._get_token()
        if not token:
            return {"ok": False, "reason": "auth_failed"}

        row = ["" if v is None else v for v in values]
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                if headers:
                    await self._ensure_header(client, token, tab, headers, target_sheet_id=sid)
                else:
                    cache_key = f"{sid}:{tab}"
                    if cache_key not in self._header_checked:
                        self._header_checked.add(cache_key)
                        await self._ensure_tab(client, token, tab, target_sheet_id=sid)

                r = await client.post(
                    f"{SHEETS_API}/{sid}/values/{self._a1(tab, 'A1')}:append",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "valueInputOption": "USER_ENTERED",
                        "insertDataOption": "INSERT_ROWS",
                    },
                    json={"values": [row]},
                )
                if r.status_code >= 300:
                    log.error("gsheets.append_failed", status=r.status_code, body=r.text[:300])
                    return {"ok": False, "reason": f"http_{r.status_code}", "detail": r.text[:200]}

                updated = r.json().get("updates", {})
                log.info("gsheets.row_appended", tab=tab, cells=updated.get("updatedCells"))
                return {
                    "ok": True,
                    "tab": tab,
                    "updated_range": updated.get("updatedRange", ""),
                }
        except Exception as e:
            log.error("gsheets.append_exception", error=str(e))
            return {"ok": False, "reason": "exception", "detail": str(e)}

    def queue_row(self, row: dict[str, Any], call_id: str | None = None) -> None:
        """Queue a failed row payload to disk for background retry."""
        try:
            qdir = _queue_dir()
            fname = f"{call_id or uuid.uuid4().hex}.json"
            fpath = os.path.join(qdir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(row, f)
            log.info("gsheets.queued_to_disk", file=fname)
        except Exception as e:
            log.error("gsheets.queue_to_disk_failed", error=str(e))

    async def append_call_outcome(
        self,
        row: dict[str, Any],
        queue_on_failure: bool = True,
        tenant_id: str | None = None,
        sheet_id: str | None = None,
        tab: str | None = None,
    ) -> dict[str, Any]:
        """Append a call-outcome row using canonical column order with retry queue."""
        resolved_sheet_id = sheet_id
        resolved_tab = tab
        tenant = tenant_id or row.get("tenant") or row.get("tenant_id")
        if not resolved_sheet_id and tenant:
            try:
                from ..db import Tenant, session_scope
                with session_scope() as db:
                    t = db.get(Tenant, str(tenant))
                    if t and t.google_sheet_id:
                        resolved_sheet_id = t.google_sheet_id
                        resolved_tab = resolved_tab or t.google_sheet_tab
            except Exception:
                pass

        resolved_tab = resolved_tab or get_settings().google_sheet_tab

        values = [
            row.get("timestamp", ""),
            row.get("call_id", ""),
            row.get("caller_phone", ""),
            row.get("caller_name", ""),
            row.get("company", ""),
            "Yes" if row.get("verified") else "No",
            row.get("language", ""),
            row.get("reason", ""),
            row.get("solution", ""),
            row.get("resolution_status", ""),
            row.get("satisfaction", ""),
            "Yes" if row.get("follow_up_required") else "No",
            "Yes" if row.get("escalated") else "No",
            row.get("duration_sec", 0),
            row.get("related_order", ""),
            row.get("tenant", "") or (str(tenant) if tenant else ""),
            row.get("question", ""),
            row.get("answer", ""),
            row.get("turn_latency_ms", ""),
        ]
        kwargs: dict[str, Any] = {
            "tab": resolved_tab,
            "headers": CALL_LOG_HEADERS,
        }
        if resolved_sheet_id:
            try:
                import inspect
                sig = inspect.signature(self.append_row)
                if "target_sheet_id" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                    kwargs["target_sheet_id"] = resolved_sheet_id
            except Exception:
                kwargs["target_sheet_id"] = resolved_sheet_id

        res = await self.append_row(values, **kwargs)
        if not res.get("ok") and queue_on_failure and (resolved_sheet_id or self.is_configured()):
            self.queue_row(row, call_id=row.get("call_id"))
        return res

    async def append_email_summary(self, email_entry: dict[str, Any], tab: str | None = None) -> dict[str, Any]:
        """Append an email summary row to Google Sheets under the Email Log tab."""
        s = get_settings()
        tab_name = tab or s.google_sheet_email_tab
        values = [
            email_entry.get("timestamp", ""),
            email_entry.get("message_id", ""),
            email_entry.get("sender", ""),
            email_entry.get("subject", ""),
            email_entry.get("category", "General"),
            email_entry.get("priority", "MEDIUM"),
            email_entry.get("summary", ""),
            "Yes" if email_entry.get("action_required") else "No",
            email_entry.get("linked_order", ""),
        ]
        return await self.append_row(
            values,
            tab=tab_name,
            headers=EMAIL_LOG_HEADERS,
        )

    async def process_retry_queue(self) -> int:
        """Drain queued writes from disk. Returns count of successfully sent items."""
        if not self.is_configured():
            return 0

        qdir = _queue_dir()
        files = glob.glob(os.path.join(qdir, "*.json"))
        if not files:
            return 0

        success_count = 0
        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    row = json.load(f)
                res = await self.append_call_outcome(row, queue_on_failure=False)
                if res.get("ok"):
                    os.remove(fpath)
                    call_id = row.get("call_id")
                    if call_id:
                        await _mark_call_sheet_synced(call_id)
                    success_count += 1
                    log.info("gsheets.retry_success", file=os.path.basename(fpath))
            except Exception as e:
                log.warning("gsheets.retry_item_failed", file=os.path.basename(fpath), error=str(e))

        return success_count


async def _mark_call_sheet_synced(call_id: str) -> None:
    try:
        from ..db import Call, async_session_scope
        from sqlalchemy import update
        async with async_session_scope() as db:
            await db.execute(update(Call).where(Call.id == call_id).values(sheet_synced=1))
    except Exception as e:
        log.warning("gsheets.db_sync_update_failed", call_id=call_id, error=str(e))


def get_sheets_client() -> GoogleSheetsClient:
    return GoogleSheetsClient.instance()
