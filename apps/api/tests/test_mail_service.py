"""Unit tests for Phase 3 typed transactional email service."""
import pytest
import respx
import httpx
from voxflow_api.config import get_settings
from voxflow_api.services.mail import (
    RESEND_API_URL,
    WelcomeEmailParams,
    PasswordResetEmailParams,
    InvoiceReceiptEmailParams,
    EscalationSummaryEmailParams,
    send_welcome_email,
    send_password_reset_email,
    send_invoice_receipt_email,
    send_escalation_summary_email,
    render_welcome_html,
    render_password_reset_html,
    render_invoice_receipt_html,
    render_escalation_summary_html,
)


def test_render_welcome_html():
    params = WelcomeEmailParams(
        recipient="test@acmelogistics.co.uk",
        company_name="Acme Logistics UK",
        admin_name="Sarah Connor",
        phone_number="+44 20 7946 0991",
    )
    html = render_welcome_html(params)
    assert "Acme Logistics UK" in html
    assert "Sarah Connor" in html
    assert "+44 20 7946 0991" in html
    assert "British English (en-GB)" in html
    assert "Launch Operations Console" in html


def test_render_password_reset_html():
    params = PasswordResetEmailParams(
        recipient="operator@acmelogistics.co.uk",
        reset_url="https://voxflow.ai/reset?token=xyz123",
        user_name="David",
        expires_in_minutes=45,
    )
    html = render_password_reset_html(params)
    assert "Reset Your VoxFlow Password" in html
    assert "https://voxflow.ai/reset?token=xyz123" in html
    assert "45 minutes" in html


def test_render_invoice_receipt_html():
    params = InvoiceReceiptEmailParams(
        recipient="billing@acmelogistics.co.uk",
        company_name="Acme Logistics UK",
        invoice_id="in_uk_998811",
        amount_gbp="£449.00",
        period_end="31 Oct 2026",
        pdf_url="https://stripe.com/invoice.pdf",
        hosted_url="https://stripe.com/hosted/invoice",
    )
    html = render_invoice_receipt_html(params)
    assert "in_uk_998811" in html
    assert "£449.00" in html
    assert "20% UK VAT Included" in html
    assert "Download PDF" in html


def test_render_escalation_summary_html():
    params = EscalationSummaryEmailParams(
        recipient="ops@acmelogistics.co.uk",
        company_name="Acme Logistics UK",
        escalation_id="call_999",
        caller_phone="+44 7700 900077",
        reason="Driver stranded at Gate B without valid booking PIN",
        priority="urgent",
    )
    html = render_escalation_summary_html(params)
    assert "Human Operator Required" in html
    assert "call_999" in html
    assert "+44 7700 900077" in html
    assert "Driver stranded at Gate B" in html
    assert "URGENT" in html


@pytest.mark.asyncio
async def test_mail_dispatch_in_sandbox_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "resend_api_key", "")
    params = WelcomeEmailParams(
        recipient="sandbox@example.com",
        company_name="Sandbox Corp",
    )
    result = await send_welcome_email(params)
    assert result["status"] == "sandbox_mode"
    assert result["id"] == "mock_simulated_email_id"


@pytest.mark.asyncio
@respx.mock
async def test_mail_dispatch_with_real_api_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "resend_api_key", "re_live_key_valid_123")
    monkeypatch.setattr(get_settings(), "resend_from_email", "VoxFlow <hello@voxflow.ai>")

    route = respx.post(RESEND_API_URL).respond(
        status_code=200,
        json={"id": "email_msg_001"},
    )

    params = InvoiceReceiptEmailParams(
        recipient="finance@haulage.co.uk",
        company_name="Haulage Express",
        invoice_id="in_101",
        amount_gbp="£149.00",
    )
    result = await send_invoice_receipt_email(params)

    assert route.called
    assert result["status"] == "delivered"
    assert result["id"] == "email_msg_001"
