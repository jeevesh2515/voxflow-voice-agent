"""Google Sheets writer for the call-outcome log.

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

* **Token reuse.** Tokens are cached until 60s before expiry, so a busy call
  centre isn't re-minting JWTs on every row.

Setup is documented in SETUP.md (create service account → download JSON →
share the spreadsheet with the service-account email as Editor).
"""

from __future__ import annotations

import asyncio
import json
import time
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
]


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
    def is_configured(cls) -> bool:
        s = get_settings()
        if not s.sheets_enabled:
            return False
        if not s.google_sheet_id:
            return False
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
        """Quote a tab name for A1 notation.

        Google requires single quotes around any sheet name that is not a bare
        alphanumeric token, and internal quotes are escaped by doubling. The
        default tab here is "Call Log" — the space alone makes `Call Log!A1`
        unparseable, which Google reports as

            400 Unable to parse range: Call Log!A1

        an error that reads like a permissions or missing-sheet problem and is
        neither.
        """
        if not tab.replace("_", "").isalnum():
            tab = "'" + tab.replace("'", "''") + "'"
        return f"{tab}!{ref}"

    async def _ensure_tab(self, client: httpx.AsyncClient, token: str, tab: str) -> bool:
        """Create the tab if the spreadsheet does not have it yet.

        A new spreadsheet has one sheet called "Sheet1", so the configured tab
        never exists on first run. Creating it means the operator shares a blank
        spreadsheet and everything else is automatic — and it removes the other
        cause of "Unable to parse range", so that error can only ever mean the
        syntax problem `_a1` now prevents.
        """
        s = get_settings()
        auth = {"Authorization": f"Bearer {token}"}
        r = await client.get(
            f"{SHEETS_API}/{s.google_sheet_id}",
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
            f"{SHEETS_API}/{s.google_sheet_id}:batchUpdate",
            headers=auth,
            json={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
        )
        if r.status_code >= 300:
            log.warning("gsheets.tab_create_failed", tab=tab, status=r.status_code, body=r.text[:200])
            return False
        log.info("gsheets.tab_created", tab=tab, existing=titles)
        return True

    async def _ensure_header(self, client: httpx.AsyncClient, token: str, tab: str, headers: list[str]) -> None:
        """Create the tab and write the header row, once per process."""
        s = get_settings()
        if tab in self._header_checked:
            return
        self._header_checked.add(tab)

        await self._ensure_tab(client, token, tab)

        rng = self._a1(tab, "A1:Z1")
        try:
            r = await client.get(
                f"{SHEETS_API}/{s.google_sheet_id}/values/{rng}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code != 200:
                log.warning("gsheets.header_read_failed", status=r.status_code, body=r.text[:200])
                return
            if r.json().get("values"):
                return  # already has a header

            await client.put(
                f"{SHEETS_API}/{s.google_sheet_id}/values/{rng}",
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
    ) -> dict[str, Any]:
        """Append one row to the configured spreadsheet.

        Returns {"ok": bool, ...}. Never raises.
        """
        s = get_settings()
        if not self.is_configured():
            return {"ok": False, "reason": "sheets_not_configured"}

        tab = tab or s.google_sheet_tab
        token = await self._get_token()
        if not token:
            return {"ok": False, "reason": "auth_failed"}

        row = ["" if v is None else v for v in values]
        try:
            # 6s, not 10: this runs on the call path's coat-tails and a
            # long hang is worse than a missed row (Postgres still has it).
            async with httpx.AsyncClient(timeout=6.0) as client:
                if headers:
                    await self._ensure_header(client, token, tab, headers)
                elif tab not in self._header_checked:
                    self._header_checked.add(tab)
                    await self._ensure_tab(client, token, tab)

                r = await client.post(
                    f"{SHEETS_API}/{s.google_sheet_id}/values/{self._a1(tab, 'A1')}:append",
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
            # A phone call is in progress. Log it and move on.
            log.error("gsheets.append_exception", error=str(e))
            return {"ok": False, "reason": "exception", "detail": str(e)}

    async def append_call_outcome(self, row: dict[str, Any]) -> dict[str, Any]:
        """Append a call-outcome row using the canonical column order."""
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
        ]
        return await self.append_row(
            values,
            tab=get_settings().google_sheet_tab,
            headers=CALL_LOG_HEADERS,
        )


def get_sheets_client() -> GoogleSheetsClient:
    return GoogleSheetsClient.instance()
