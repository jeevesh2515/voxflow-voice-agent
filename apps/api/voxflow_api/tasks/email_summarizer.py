"""Email Summarizer Agent — processes incoming business emails, summarizes them via LLM,
persists records to Postgres (CommunicationLog), updates Google Sheets (Email Log tab),
and maintains persistent memory (AgentState) for zero lost information and idempotency.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import AgentState, CommunicationLog, async_session_scope
from ..integrations.gmail import EmailMessage, get_gmail_client
from ..integrations.gsheets import get_sheets_client
from ..llm import get_llm
from ..llm.base import ChatTurn
from ..logging import get_logger

log = get_logger(__name__)

EMAIL_SUMMARIZER_PROMPT = """You are the Operations Intelligence Email Assistant for an FMCG & Supply Chain company.
Analyze the following inbound email from a customer, supplier, or logistics partner.

EMAIL METADATA:
From: {sender}
Subject: {subject}
Date: {date}

EMAIL BODY:
{body}

Extract and format the response as valid JSON with the following keys:
1. "category": Choose one of ["Order Placement", "Order/PO Status Query", "Logistics/Dispatch Update", "Stock/Inventory Inquiry", "General Support", "Spam/Unrelated"].
2. "priority": Choose one of ["HIGH", "MEDIUM", "LOW"]. (Mark HIGH if urgent delivery inquiry, stock outage, or new order).
3. "summary": Exactly 2-3 concise, professional sentences in English explaining who contacted, what specific order/SKU they inquired about, and what action is needed.
4. "action_required": Boolean (true or false).
5. "linked_order": Extract any PO number (e.g. PO-1717000000-001) or shipment tracking number mentioned, or empty string "" if none.

Return ONLY the raw JSON object, without markdown formatting or code blocks.
"""


class EmailSummarizerAgent:
    """Autonomous agent that checks emails, generates concise summaries, and records logs."""

    def __init__(self, tenant_id: str = "varun") -> None:
        self.tenant_id = tenant_id
        self.settings = get_settings()
        self.gmail = get_gmail_client()
        self.sheets = get_sheets_client()

    async def get_processed_message_ids(self) -> set[str]:
        """Fetch previously processed email message IDs from persistent AgentState."""
        state_key = f"processed_email_ids_{self.tenant_id}"
        async with async_session_scope() as db:
            state = (
                await db.execute(select(AgentState).where(AgentState.key == state_key))
            ).scalars().first()
            if not state:
                return set()
            try:
                data = json.loads(state.value_json or "[]")
                return set(data) if isinstance(data, list) else set()
            except Exception:
                return set()

    async def record_processed_message_id(self, message_id: str) -> None:
        """Persist processed email message ID to avoid duplicate processing."""
        state_key = f"processed_email_ids_{self.tenant_id}"
        async with async_session_scope() as db:
            state = (
                await db.execute(select(AgentState).where(AgentState.key == state_key))
            ).scalars().first()
            if not state:
                state = AgentState(
                    key=state_key,
                    tenant_id=self.tenant_id,
                    value_json=json.dumps([message_id]),
                )
                db.add(state)
            else:
                try:
                    current = json.loads(state.value_json or "[]")
                except Exception:
                    current = []
                if message_id not in current:
                    current.append(message_id)
                    # keep last 500 IDs to avoid unbounded growth
                    if len(current) > 500:
                        current = current[-500:]
                    state.value_json = json.dumps(current)
                    state.updated_at = datetime.now(timezone.utc)
            await db.flush()

    async def summarize_email_with_llm(self, msg: EmailMessage) -> dict[str, Any]:
        """Use LLM to generate category, priority, and 2-3 sentence executive summary."""
        llm = get_llm()
        prompt = EMAIL_SUMMARIZER_PROMPT.format(
            sender=msg.sender,
            subject=msg.subject,
            date=msg.date.isoformat(),
            body=msg.body or msg.snippet,
        )

        turns = [
            ChatTurn(role="system", content="You are a precise B2B supply chain operations intelligence assistant."),
            ChatTurn(role="user", content=prompt),
        ]

        try:
            resp = await llm.chat(turns, temperature=0.1, max_tokens=300)
            content = resp.content.strip()
            # Clean JSON markdown if model wrapped it in ```json ... ```
            if content.startswith("```"):
                content = re.sub(r"^```[a-zA-Z]*\n", "", content)
                content = re.sub(r"\n```$", "", content)
            parsed = json.loads(content)
            return {
                "category": parsed.get("category", "General Support"),
                "priority": parsed.get("priority", "MEDIUM"),
                "summary": parsed.get("summary", msg.snippet or "Inbound email received."),
                "action_required": bool(parsed.get("action_required", False)),
                "linked_order": parsed.get("linked_order", ""),
            }
        except Exception as e:
            log.warning("email_summarizer.llm_fallback", error=str(e))
            # Fallback heuristic analysis
            category = "General Support"
            priority = "MEDIUM"
            linked_order = ""

            sub_lower = msg.subject.lower()
            if "po-" in sub_lower or "po-" in msg.body.lower():
                category = "Order/PO Status Query"
                match = re.search(r"PO-\d+-\w+", msg.subject + " " + msg.body)
                if match:
                    linked_order = match.group(0)
            elif "order" in sub_lower or "inquiry" in sub_lower:
                category = "Order Placement"
                priority = "HIGH"
            elif "shipment" in sub_lower or "tracking" in sub_lower:
                category = "Logistics/Dispatch Update"

            summary = f"Received inquiry from {msg.sender} regarding '{msg.subject}'. Key context: {msg.snippet[:150]}..."
            return {
                "category": category,
                "priority": priority,
                "summary": summary,
                "action_required": True,
                "linked_order": linked_order,
            }

    async def run_sync_cycle(self, limit: int = 15) -> dict[str, Any]:
        """Execute one complete email summarization and synchronization cycle."""
        t0 = time.time()
        log.info("email_summarizer.cycle_started", tenant_id=self.tenant_id)

        processed_ids = await self.get_processed_message_ids()
        emails = await self.gmail.fetch_recent_emails(limit=limit)

        new_count = 0
        sheets_synced = 0
        summaries: list[dict[str, Any]] = []
        ist = timezone(timedelta(hours=5, minutes=30))

        for msg in emails:
            if msg.message_id in processed_ids:
                continue

            summary_info = await self.summarize_email_with_llm(msg)
            now_ist = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

            # 1. Save to Database (CommunicationLog)
            comm_id = f"comm-email-{uuid.uuid4().hex[:6]}"
            async with async_session_scope() as db:
                comm = CommunicationLog(
                    id=comm_id,
                    tenant_id=self.tenant_id,
                    channel="email",
                    recipient=msg.sender,
                    subject=f"[{summary_info['category']}] {msg.subject}",
                    body=f"Summary: {summary_info['summary']}\nPriority: {summary_info['priority']}\nAction Required: {summary_info['action_required']}\nLinked Order: {summary_info['linked_order']}",
                    status="summarized",
                )
                db.add(comm)

            # 2. Append to Google Sheets Email Log tab
            sheet_payload = {
                "timestamp": now_ist,
                "message_id": msg.message_id,
                "sender": msg.sender,
                "subject": msg.subject,
                "category": summary_info["category"],
                "priority": summary_info["priority"],
                "summary": summary_info["summary"],
                "action_required": summary_info["action_required"],
                "linked_order": summary_info["linked_order"],
            }

            res = await self.sheets.append_email_summary(sheet_payload)
            if res.get("ok"):
                sheets_synced += 1

            # 3. Mark processed in persistent memory
            await self.record_processed_message_id(msg.message_id)

            new_count += 1
            summaries.append({
                "message_id": msg.message_id,
                "sender": msg.sender,
                "subject": msg.subject,
                **summary_info,
                "sheet_synced": res.get("ok", False),
            })

        # Update last run state
        state_key = f"email_summarizer_last_run_{self.tenant_id}"
        async with async_session_scope() as db:
            state = (
                await db.execute(select(AgentState).where(AgentState.key == state_key))
            ).scalars().first()
            now_iso = datetime.now(timezone.utc).isoformat()
            if not state:
                db.add(AgentState(key=state_key, tenant_id=self.tenant_id, value_json=json.dumps({"last_run": now_iso, "total_processed": new_count})))
            else:
                state.value_json = json.dumps({"last_run": now_iso, "total_processed": new_count})
                state.updated_at = datetime.now(timezone.utc)

        elapsed = round(time.time() - t0, 2)
        log.info(
            "email_summarizer.cycle_complete",
            processed=new_count,
            sheets_synced=sheets_synced,
            elapsed_sec=elapsed,
        )

        return {
            "ok": True,
            "tenant_id": self.tenant_id,
            "processed_count": new_count,
            "sheets_synced_count": sheets_synced,
            "elapsed_sec": elapsed,
            "summaries": summaries,
        }
