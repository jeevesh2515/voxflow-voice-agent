"""Typed transactional email service wrapping Resend REST API (Phase 3).

Provides typed parameter models and high-fidelity, accessible HTML/text templates
for VoxFlow's core operational events:
1. Workspace Welcome (`send_welcome_email`)
2. Password Reset (`send_password_reset_email`)
3. Invoice Receipt (`send_invoice_receipt_email`)
4. Operational Escalation Summary (`send_escalation_summary_email`)

When RESEND_API_KEY is unset or in mock mode, operations record safe dispatches
without raising network errors.
"""
from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, Field
import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


# -----------------------------------------------------------------------------
# Parameter Models
# -----------------------------------------------------------------------------

class WelcomeEmailParams(BaseModel):
    recipient: str = Field(..., description="Recipient email address")
    company_name: str = Field(..., description="Customer organization / workspace name")
    admin_name: str = Field(default="Team Member", description="Admin user display name")
    login_url: str = Field(default="https://voxflow-voice-agent.vercel.app/sign-in", description="Dashboard login URL")
    phone_number: str | None = Field(default=None, description="Assigned inbound voice number if provisioned")


class PasswordResetEmailParams(BaseModel):
    recipient: str = Field(..., description="Recipient email address")
    reset_url: str = Field(..., description="Secure password reset link with token")
    user_name: str = Field(default="Operator", description="User display name")
    expires_in_minutes: int = Field(default=60, description="Token validity duration in minutes")


class InvoiceReceiptEmailParams(BaseModel):
    recipient: str = Field(..., description="Billing contact email address")
    company_name: str = Field(..., description="Customer company name")
    invoice_id: str = Field(..., description="Stripe invoice ID or number")
    amount_gbp: str = Field(..., description="Formatted amount paid in GBP, e.g. '£149.00'")
    period_end: str | None = Field(default=None, description="Current subscription period end date")
    pdf_url: str | None = Field(default=None, description="Stripe hosted PDF download link")
    hosted_url: str | None = Field(default=None, description="Stripe customer portal invoice link")


class EscalationSummaryEmailParams(BaseModel):
    recipient: str = Field(..., description="On-call operator or escalation digest recipient")
    company_name: str = Field(..., description="Workspace company name")
    escalation_id: str = Field(..., description="Call or escalation identifier")
    caller_phone: str = Field(..., description="Caller E.164 phone or identifier")
    reason: str = Field(..., description="Summary explanation of why the call escalated")
    priority: str = Field(default="high", description="Escalation priority: low, medium, high, urgent")
    dashboard_url: str = Field(
        default="https://voxflow-voice-agent.vercel.app/dashboard/escalations",
        description="Direct link to escalation resolution queue",
    )


# -----------------------------------------------------------------------------
# HTML Template Renderers
# -----------------------------------------------------------------------------

def _base_email_layout(title: str, content_html: str, preheader: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ margin: 0; padding: 0; background-color: #07070f; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e8e0f0; }}
    table {{ border-spacing: 0; }}
    td {{ padding: 0; }}
    img {{ border: 0; }}
    .wrapper {{ width: 100%; table-layout: fixed; background-color: #07070f; padding-bottom: 40px; }}
    .main {{ background-color: #0e0e1a; margin: 0 auto; width: 100%; max-width: 600px; border: 1px solid #28283c; border-radius: 16px; overflow: hidden; }}
    .header {{ padding: 32px 36px 20px 36px; border-bottom: 1px solid #1e1e30; text-align: left; }}
    .logo {{ font-size: 20px; font-weight: 800; letter-spacing: -0.5px; color: #ffffff; text-decoration: none; }}
    .logo-accent {{ color: #ff2d78; }}
    .content {{ padding: 36px; }}
    .footer {{ padding: 24px 36px; background-color: #090914; border-top: 1px solid #1e1e30; text-align: center; font-size: 12px; color: #706880; line-height: 18px; }}
    .btn {{ display: inline-block; padding: 12px 28px; background-color: #ff2d78; color: #ffffff !important; text-decoration: none; font-weight: 700; font-size: 14px; border-radius: 8px; margin-top: 20px; }}
    .badge {{ display: inline-block; padding: 4px 10px; background-color: rgba(0, 255, 204, 0.1); color: #00ffcc; border-radius: 999px; font-size: 11px; font-family: monospace; font-weight: bold; }}
    .meta-box {{ background-color: #141424; border: 1px solid #242438; border-radius: 10px; padding: 18px; margin: 24px 0; }}
    .meta-row {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; }}
    .meta-label {{ color: #94a3b8; font-weight: 500; }}
    .meta-value {{ color: #f8fafc; font-weight: 600; font-family: monospace; }}
  </style>
</head>
<body>
  <span style="display:none;font-size:1px;color:#07070f;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">{preheader}</span>
  <center class="wrapper">
    <table class="main" width="100%">
      <tr>
        <td class="header">
          <a href="https://voxflow-voice-agent.vercel.app" class="logo">VOX<span class="logo-accent">FLOW</span></a>
          <span style="float:right;color:#00ffcc;font-family:monospace;font-size:11px;padding-top:4px;">● OPERATIONAL TRUST</span>
        </td>
      </tr>
      <tr>
        <td class="content">
          {content_html}
        </td>
      </tr>
      <tr>
        <td class="footer">
          <p style="margin:0 0 8px 0;">VoxFlow Voice Operations • AWS eu-west-2 (London) • VAT Registered</p>
          <p style="margin:0;">Need immediate operator support? Email <a href="mailto:support@voxflow.com" style="color:#00ffcc;text-decoration:none;">support@voxflow.com</a> or use the in-app Crisp chat widget.</p>
        </td>
      </tr>
    </table>
  </center>
</body>
</html>"""


def render_welcome_html(params: WelcomeEmailParams) -> str:
    phone_snippet = ""
    if params.phone_number:
        phone_snippet = f"""
        <div class="meta-row">
          <span class="meta-label">Assigned UK Voice Line:</span>
          <span class="meta-value">{params.phone_number}</span>
        </div>"""

    content = f"""
    <span class="badge">WORKSPACE PROVISIONED</span>
    <h1 style="color:#ffffff;font-size:24px;margin:16px 0 12px 0;font-weight:700;">Welcome to VoxFlow, {params.admin_name}!</h1>
    <p style="color:#cbd5e1;font-size:14px;line-height:22px;margin:0 0 16px 0;">
      Your autonomous voice operations core for <strong>{params.company_name}</strong> is live and ready for high-stakes transport and order calls.
    </p>

    <div class="meta-box">
      <div class="meta-row">
        <span class="meta-label">Workspace Name:</span>
        <span class="meta-value">{params.company_name}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Primary Dialect:</span>
        <span class="meta-value">British English (en-GB)</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Inference Engine:</span>
        <span class="meta-value">Groq Sub-200ms Glass-to-Glass</span>
      </div>
      {phone_snippet}
    </div>

    <p style="color:#cbd5e1;font-size:14px;line-height:22px;margin:0 0 24px 0;">
      You can now configure caller PIN verification policies, connect your live spreadsheets or ERP, and test in-browser audio calls with zero telecom overhead.
    </p>

    <center>
      <a href="{params.login_url}" class="btn">Launch Operations Console →</a>
    </center>
    """
    return _base_email_layout("Welcome to VoxFlow", content, preheader=f"Your workspace for {params.company_name} is ready.")


def render_password_reset_html(params: PasswordResetEmailParams) -> str:
    content = f"""
    <span class="badge" style="color:#ff2d78;background:rgba(255,45,120,0.1);">SECURITY ACTION</span>
    <h1 style="color:#ffffff;font-size:24px;margin:16px 0 12px 0;font-weight:700;">Reset Your VoxFlow Password</h1>
    <p style="color:#cbd5e1;font-size:14px;line-height:22px;margin:0 0 16px 0;">
      Hello {params.user_name}, we received a request to reset your console password. Click the button below to securely configure a new credential.
    </p>

    <center style="margin:28px 0;">
      <a href="{params.reset_url}" class="btn">Reset Password Securely →</a>
    </center>

    <div class="meta-box" style="margin-top:20px;">
      <div class="meta-row">
        <span class="meta-label">Link Expiration:</span>
        <span class="meta-value">{params.expires_in_minutes} minutes</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Security Protocol:</span>
        <span class="meta-value">Single-use token with HMAC-SHA256</span>
      </div>
    </div>

    <p style="color:#94a3b8;font-size:12px;line-height:18px;margin:20px 0 0 0;">
      If you did not initiate this request, your account remains secure and no further action is required. Please ignore this email.
    </p>
    """
    return _base_email_layout("Reset Your VoxFlow Password", content, preheader="Secure password reset request for your VoxFlow account.")


def render_invoice_receipt_html(params: InvoiceReceiptEmailParams) -> str:
    links = []
    if params.hosted_url:
        links.append(f'<a href="{params.hosted_url}" style="color:#00ffcc;text-decoration:none;font-size:13px;font-weight:bold;">View Online Receipt ↗</a>')
    if params.pdf_url:
        links.append(f'<a href="{params.pdf_url}" style="color:#00ffcc;text-decoration:none;font-size:13px;font-weight:bold;margin-left:16px;">Download PDF Invoice ↗</a>')
    links_html = "".join(links) or '<span style="color:#94a3b8;font-size:12px;">Available in your Stripe billing portal</span>'

    period_row = ""
    if params.period_end:
        period_row = f"""
        <div class="meta-row">
          <span class="meta-label">Next Renewal Date:</span>
          <span class="meta-value">{params.period_end}</span>
        </div>"""

    content = f"""
    <span class="badge">PAYMENT CONFIRMED</span>
    <h1 style="color:#ffffff;font-size:24px;margin:16px 0 12px 0;font-weight:700;">Payment Receipt & VAT Invoice</h1>
    <p style="color:#cbd5e1;font-size:14px;line-height:22px;margin:0 0 16px 0;">
      Thank you for your payment. Your VoxFlow subscription for <strong>{params.company_name}</strong> has been successfully renewed.
    </p>

    <div class="meta-box">
      <div class="meta-row">
        <span class="meta-label">Invoice Number:</span>
        <span class="meta-value">{params.invoice_id}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Total Amount Paid:</span>
        <span class="meta-value" style="color:#00ffcc;font-size:15px;">{params.amount_gbp}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">VAT Status:</span>
        <span class="meta-value">20% UK VAT Included</span>
      </div>
      {period_row}
    </div>

    <p style="color:#cbd5e1;font-size:14px;line-height:22px;margin:0 0 20px 0;">
      Your billing records and meter usage logs are updated in real time.
    </p>

    <div style="margin:24px 0 10px 0;text-align:center;">
      {links_html}
    </div>
    """
    return _base_email_layout(f"Payment Receipt: {params.invoice_id}", content, preheader=f"Receipt for your payment of {params.amount_gbp} to VoxFlow.")


def render_escalation_summary_html(params: EscalationSummaryEmailParams) -> str:
    color = "#ff4444" if params.priority in ("urgent", "high") else "#ffe04a"
    content = f"""
    <span class="badge" style="color:{color};background:rgba(255,68,68,0.1);">URGENT ESCALATION</span>
    <h1 style="color:#ffffff;font-size:24px;margin:16px 0 12px 0;font-weight:700;">Human Operator Required</h1>
    <p style="color:#cbd5e1;font-size:14px;line-height:22px;margin:0 0 16px 0;">
      A voice session for <strong>{params.company_name}</strong> triggered an escalation rule requiring human operator follow-up.
    </p>

    <div class="meta-box" style="border-left: 4px solid {color};">
      <div class="meta-row">
        <span class="meta-label">Escalation ID:</span>
        <span class="meta-value">{params.escalation_id}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Caller Phone:</span>
        <span class="meta-value">{params.caller_phone}</span>
      </div>
      <div class="meta-row">
        <span class="meta-label">Priority:</span>
        <span class="meta-value" style="color:{color};text-transform:uppercase;">{params.priority}</span>
      </div>
      <div class="meta-row" style="flex-direction:column;gap:4px;margin-top:6px;">
        <span class="meta-label">Escalation Reason:</span>
        <span style="color:#f8fafc;font-size:13px;line-height:18px;">{params.reason}</span>
      </div>
    </div>

    <center>
      <a href="{params.dashboard_url}" class="btn" style="background-color:#ff4444;">Resolve in Escalation Queue →</a>
    </center>

    <p style="color:#94a3b8;font-size:12px;line-height:18px;margin:24px 0 0 0;text-align:center;">
      Caller audio recording and complete turn transcript are available inside the secure dashboard.
    </p>
    """
    return _base_email_layout(f"Escalation Alert: {params.escalation_id}", content, preheader=f"Action required: Call from {params.caller_phone} escalated.")


# -----------------------------------------------------------------------------
# Dispatch Service
# -----------------------------------------------------------------------------

async def _send_resend_email(
    to: str | list[str],
    subject: str,
    html: str,
    text: str,
    from_email: str | None = None,
) -> dict[str, Any]:
    """Execute raw HTTP POST against Resend REST API or simulate in sandbox."""
    settings = get_settings()
    api_key = (settings.resend_api_key or "").strip()
    sender = (from_email or settings.resend_from_email or "VoxFlow <onboarding@resend.dev>").strip()

    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        return {"status": "skipped", "reason": "no_recipients"}

    if not api_key:
        logger.info(
            "Resend API key not configured; simulated email dispatch to %s (subject: %s)",
            recipients,
            subject,
        )
        return {
            "id": "mock_simulated_email_id",
            "status": "sandbox_mode",
            "to": recipients,
            "subject": subject,
        }

    payload = {
        "from": sender,
        "to": recipients,
        "subject": subject,
        "html": html,
        "text": text,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(RESEND_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            email_id = data.get("id", "sent")
            logger.info("Resend email delivered: id=%s to=%s subject=%s", email_id, recipients, subject)
            return {
                "id": email_id,
                "status": "delivered",
                "to": recipients,
                "subject": subject,
            }
        except httpx.HTTPStatusError as exc:
            logger.error("Resend API HTTP %s: %s", exc.response.status_code, exc.response.text)
            return {
                "status": "failed",
                "error": f"HTTP {exc.response.status_code}: {exc.response.text}",
                "to": recipients,
            }
        except Exception as exc:
            logger.error("Resend dispatch connection error: %s", exc)
            return {
                "status": "failed",
                "error": str(exc),
                "to": recipients,
            }


# -----------------------------------------------------------------------------
# Public High-Level Typed APIs
# -----------------------------------------------------------------------------

async def send_welcome_email(params: WelcomeEmailParams) -> dict[str, Any]:
    subject = f"Welcome to VoxFlow — {params.company_name}"
    html = render_welcome_html(params)
    text = (
        f"Welcome to VoxFlow, {params.admin_name}!\n\n"
        f"Your voice operations workspace for {params.company_name} is active.\n"
        f"Login: {params.login_url}\n"
        + (f"Voice Line: {params.phone_number}\n" if params.phone_number else "")
    )
    return await _send_resend_email(params.recipient, subject, html, text)


async def send_password_reset_email(params: PasswordResetEmailParams) -> dict[str, Any]:
    subject = "Reset Your VoxFlow Password"
    html = render_password_reset_html(params)
    text = (
        f"Hello {params.user_name},\n\n"
        f"Reset your VoxFlow password using the link below (valid for {params.expires_in_minutes} minutes):\n"
        f"{params.reset_url}\n\n"
        "If you did not request this, you can safely ignore this message."
    )
    return await _send_resend_email(params.recipient, subject, html, text)


async def send_invoice_receipt_email(params: InvoiceReceiptEmailParams) -> dict[str, Any]:
    subject = f"Payment Receipt: {params.invoice_id} — VoxFlow"
    html = render_invoice_receipt_html(params)
    text = (
        f"Payment Receipt for {params.company_name}\n"
        f"Invoice: {params.invoice_id}\n"
        f"Amount Paid: {params.amount_gbp}\n"
        + (f"Next Period End: {params.period_end}\n" if params.period_end else "")
        + (f"Hosted Receipt: {params.hosted_url}\n" if params.hosted_url else "")
        + (f"Download PDF: {params.pdf_url}\n" if params.pdf_url else "")
    )
    return await _send_resend_email(params.recipient, subject, html, text)


async def send_escalation_summary_email(params: EscalationSummaryEmailParams) -> dict[str, Any]:
    subject = f"[{params.priority.upper()}] Escalation Alert: Call from {params.caller_phone}"
    html = render_escalation_summary_html(params)
    text = (
        f"ESCALATION ALERT ({params.priority.upper()})\n"
        f"Workspace: {params.company_name}\n"
        f"Escalation ID: {params.escalation_id}\n"
        f"Caller: {params.caller_phone}\n"
        f"Reason: {params.reason}\n\n"
        f"Resolve in queue: {params.dashboard_url}"
    )
    return await _send_resend_email(params.recipient, subject, html, text)
