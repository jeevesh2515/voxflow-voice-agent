"""Gmail integration for fetching and parsing business emails."""

from __future__ import annotations

import asyncio
import email
import imaplib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.header import decode_header

from ..config import get_settings
from ..logging import get_logger

log = get_logger(__name__)


@dataclass
class EmailMessage:
    message_id: str
    sender: str
    subject: str
    date: datetime
    body: str
    snippet: str
    has_attachments: bool = False


def _decode_mime_words(raw_header: str | None) -> str:
    """Decode RFC 2047 MIME-encoded email headers."""
    if not raw_header:
        return ""
    decoded_fragments = []
    for frag, enc in decode_header(raw_header):
        if isinstance(frag, bytes):
            try:
                decoded_fragments.append(frag.decode(enc or "utf-8", errors="replace"))
            except Exception:
                decoded_fragments.append(frag.decode("utf-8", errors="replace"))
        else:
            decoded_fragments.append(str(frag))
    return "".join(decoded_fragments).strip()


def _extract_body(msg: email.message.Message) -> str:
    """Extract plain text or cleaned HTML body from an email message."""
    text_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))
            if "attachment" in cdispo:
                continue
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text_parts.append(payload.decode(charset, errors="replace"))
            elif ctype == "text/html" and not text_parts:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    html_text = payload.decode(charset, errors="replace")
                    # simple tag strip
                    clean = re.sub(r"<[^>]+>", " ", html_text)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    text_parts.append(clean)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text_parts.append(payload.decode(charset, errors="replace"))

    full_body = "\n".join(text_parts).strip()
    return full_body[:4000]  # cap for prompt window


class GmailClient:
    """Async wrapper for Gmail operations via IMAP with fallback sample data."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.gmail_user_email and s.gmail_app_password)

    def _fetch_sync(self, limit: int = 15) -> list[EmailMessage]:
        """Fetch emails via synchronous IMAP (run in thread pool)."""
        s = get_settings()
        if not self.is_configured():
            return self._get_sample_emails()

        try:
            mail = imaplib.IMAP4_SSL(s.gmail_imap_server, s.gmail_imap_port)
            mail.login(s.gmail_user_email, s.gmail_app_password)
            mail.select("INBOX", readonly=True)

            status, messages = mail.search(None, "ALL")
            if status != "OK" or not messages[0]:
                mail.logout()
                return []

            msg_ids = messages[0].split()
            recent_ids = msg_ids[-limit:]  # take latest N emails
            recent_ids.reverse()  # newest first

            emails: list[EmailMessage] = []
            for num in recent_ids:
                status, data = mail.fetch(num, "(RFC822)")
                if status != "OK" or not data:
                    continue
                for response_part in data:
                    if isinstance(response_part, tuple):
                        raw_msg = email.message_from_bytes(response_part[1])
                        mid = _decode_mime_words(raw_msg.get("Message-ID") or f"msg-{num.decode()}")
                        sender = _decode_mime_words(raw_msg.get("From"))
                        subject = _decode_mime_words(raw_msg.get("Subject"))
                        date_str = raw_msg.get("Date")
                        
                        try:
                            dt = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.now(timezone.utc)
                        except Exception:
                            dt = datetime.now(timezone.utc)

                        body = _extract_body(raw_msg)
                        snippet = body[:200].replace("\n", " ")

                        emails.append(
                            EmailMessage(
                                message_id=mid,
                                sender=sender,
                                subject=subject or "(No Subject)",
                                date=dt,
                                body=body,
                                snippet=snippet,
                            )
                        )

            mail.logout()
            return emails
        except Exception as e:
            log.warning("gmail.fetch_failed_using_samples", error=str(e))
            return self._get_sample_emails()

    def _get_sample_emails(self) -> list[EmailMessage]:
        """Realistic sample emails for testing when Gmail App Password is not yet set."""
        now = datetime.now(timezone.utc)
        return [
            EmailMessage(
                message_id="sample-msg-001@sharma-beverages.com",
                sender="Rajesh Sharma <rajesh@sharmabeverages.com>",
                subject="URGENT: Purchase Order PO-1717000000-001 Dispatch Status & Tracking",
                date=now,
                body="Dear VoxFlow Team,\n\nWe placed order PO-1717000000-001 for 500 cases of Pepsi 250ml last week. Could you please confirm if the consignment has passed the Ghaziabad hub and when we can expect delivery at our Gurgaon warehouse? Our retail clients are waiting for the stock.\n\nBest regards,\nRajesh Sharma\nSharma Beverages Wholesale",
                snippet="We placed order PO-1717000000-001 for 500 cases of Pepsi 250ml last week...",
            ),
            EmailMessage(
                message_id="sample-msg-002@verma-traders.in",
                sender="Amit Verma <amit@vermatraders.in>",
                subject="New Order Inquiry: 200 cases Mountain Dew 750ml",
                date=now,
                body="Hello Team,\n\nWe would like to place a new bulk purchase order for 200 cases of Mountain Dew 750ml (Pack of 12) for our Noida distribution center. Please let us know the current wholesale unit pricing and if stock is readily available for dispatch by Friday.\n\nThanks,\nAmit Verma\nVerma Traders",
                snippet="We would like to place a new bulk purchase order for 200 cases of Mountain Dew 750ml...",
            ),
            EmailMessage(
                message_id="sample-msg-003@vrl-logistics.com",
                sender="Dispatch Desk <tracking@vrl-logistics.com>",
                subject="Shipment Update: VRL-998877 Out for Local Hub Delivery",
                date=now,
                body="Consignment VRL-998877 linked to PO-1717000000-001 is on schedule. Current location: Ghaziabad Regional Hub. Estimated delivery window: Tomorrow morning between 10:00 AM - 1:00 PM IST.\n\nVehicle No: HR-55-AB-1234\nDriver Contact: +91-9876543210",
                snippet="Consignment VRL-998877 linked to PO-1717000000-001 is on schedule. Current location: Ghaziabad...",
            ),
        ]

    async def fetch_recent_emails(self, limit: int = 15) -> list[EmailMessage]:
        """Async fetch wrapper offloading network IO to thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self._fetch_sync(limit=limit))


_gmail_client_instance: GmailClient | None = None


def get_gmail_client() -> GmailClient:
    global _gmail_client_instance
    if _gmail_client_instance is None:
        _gmail_client_instance = GmailClient()
    return _gmail_client_instance
